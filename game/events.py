"""Executable, evidence-driven incident scripts for all 96 design seeds.

Every script has frozen facts, visible evidence, two actionable alternatives,
optional de-escalation, a confirmation boundary, execution and a follow-up.
These are authored vignettes, not 96 bespoke action minigames.
"""
from __future__ import annotations
from .jsoncopy import tree_copy
from .content import EVENT_SEEDS

# label A, label B. Both are viable; evidence and costs differ, not a morality meter.
CHOICES = {
"MB": [
("Chọn quà theo ngân sách", "Hẹn khách xem thêm hai mẫu"),
("Gửi bổ sung phần thiếu", "Hoàn phần thiếu · 15 xu"),
("Đổi đúng cỡ còn trong kho", "Nhận hẹn đổi vào ngày sau"),
("Đối chiếu và giải thích hóa đơn", "Cùng khách kiểm lại tại quầy"),
("Kiểm kệ và hỏi An", "Nhờ An đối chiếu vị trí kho"),
("Nhắc thanh toán sau khi kiểm chứng", "Nhờ bảo vệ khu phố hỗ trợ"),
("Từ chối tài trợ, vẫn phục vụ bình thường", "Tài trợ quà nhỏ · 20 xu"),
("Chỉ khu trưng bày được quay", "Đề nghị dừng quay trong tiệm"),
("Giải thích công khai, không lộ đơn", "Mời khách trao đổi riêng"),
("Liên hệ và giữ đơn thêm một nhịp", "Hủy hẹn, trả hàng về bán lẻ"),
("Áp dụng một phần dùng thử mỗi lượt", "Mời thêm phần nhỏ · 5 xu"),
("Tặng một phần quà · 15 xu", "Giải thích giới hạn, chỉ món vừa ngân sách"),
("Giữ gói hàng chờ thanh toán", "Tặng phần nhỏ · 10 xu"),
("Nhận lượng phù hợp khả năng", "Thương lượng chia thành hai lượt"),
("Nhận đúng phần đã giao, yêu cầu bù", "Điều chỉnh phiếu theo thực nhận"),
("Sửa món và hướng dẫn An kiểm nhãn", "Tự kiểm cuối, giao An sắp lại kệ"),
("Hỏi thăm và dọn vùng bị vỡ", "Nhờ phụ việc dọn, tạm rào khu vực"),
("Phục vụ theo thứ tự đã ghi", "Hỏi ý kiến người đang chờ trước"),
("Chuyển hàng vào vùng khô", "Tạm đóng góc cửa và che kệ"),
("Giữ túi, hỏi chi tiết để xác minh", "Bàn giao túi cho điểm đồ thất lạc"),
("Trấn an khách, báo bảo vệ", "Lưu dữ kiện, đi cùng khách tới điểm hỗ trợ"),
("Bật nhận hẹn và giới hạn lượt", "Nhờ hàng xóm hỗ trợ khu chờ"),
("Giải thích phạm vi hàng của tiệm", "Chuyển người phụ trách phù hợp"),
("Tổ chức góc gói quà nhỏ · 15 xu", "Mời mọi người mang vật liệu cùng làm"),
],
"PH":[
("Đối chiếu và chuẩn bị phiếu", "Nhờ cô Thu kiểm cùng"),
("Hỏi trường còn thiếu", "Giữ phiếu chờ người phụ trách"),
("Nhờ kiểm lại mã trên phiếu", "Giữ yêu cầu, không đoán theo màu"),
("Đọc mã từng hộp", "Dùng khay để so hai nhãn"),
("Điều chỉnh số lượng theo phiếu", "Nhờ Khoa kiểm cùng một lượt"),
("Tách lô không hợp lệ", "Chuyển cô Thu kiểm lô thay thế"),
("Giữ riêng hộp móp", "Gửi người phụ trách kiểm tình trạng"),
("Giữ bước kiểm, giải thích thời gian", "Nhận hẹn kiểm xong rồi tới lấy"),
("Chuyển cô Thu, không đoán", "Giữ yêu cầu chờ người phụ trách"),
("Nhận hẹn đúng mã", "Kết thúc yêu cầu theo lựa chọn khách"),
("Đối chiếu nhãn và phiếu tính", "Nhờ cô Thu cùng giải thích"),
("Giữ gói chờ xác nhận thanh toán", "Hỏi lại khách bằng thông tin giao dịch"),
("Cách ly kiện sai lô", "Từ chối nhận kiện, xin phiếu đúng"),
("Đánh dấu và tạm giữ lô", "Nhờ Khoa kiểm toàn bộ vị trí liên quan"),
("Nhận hộp vào khu chờ kiểm", "Chuyển cô Thu xử lý theo quy định"),
("Giải thích lý do phải đối chiếu", "Mời khách trao đổi riêng về phiếu"),
("Chỉ khu quay không có dữ liệu khách", "Đề nghị dừng quay tại quầy"),
("Từ chối đổi quà lấy review", "Thảo luận một bài chia sẻ quy trình"),
("Đối chiếu kệ và nhật ký chuyển", "Nhờ Khoa tìm ở khu tạm giữ"),
("Kiểm chứng rồi nhắc thanh toán", "Nhờ bảo vệ khu phố hỗ trợ"),
("Lưu phiếu, tạm ngừng bước xuất", "Hướng dẫn khách nhận hẹn"),
("Đối chiếu hai mã phiếu riêng tư", "Nhờ cô Thu liên hệ đúng người nhận"),
("Chuẩn bị danh mục đã duyệt", "Cùng Khoa kiểm khay cộng đồng"),
("Cảm ơn và nhận cây lưu niệm", "Mời khách ngồi trò chuyện một chút"),
],
"AC":[
("Phân loại và đối chiếu chứng từ", "Cùng Huy xem bản gốc"),
("Loại bản trùng có nguồn", "Gửi bản đối chiếu cho người kiểm tra"),
("Yêu cầu đúng chứng từ thiếu", "Bàn giao hồ sơ kèm phần đang chờ"),
("Gom các phiếu của lần trả", "Trình bày đối chiếu nhiều-một"),
("Ghép từng lần trả", "Ghi phần còn lại với nguồn rõ ràng"),
("Sửa dòng theo phiếu gốc", "Cùng người nhập xác nhận lại"),
("Đưa khoản về đúng kỳ", "Ghi chú khác mốc và xin xác nhận"),
("Gắn khoản hoàn với giao dịch gốc", "Trình bày riêng phần điều chỉnh"),
("Kiểm các khoản đã xác nhận", "Giữ kết luận chờ người giữ quỹ"),
("Gửi bản tạm có nhãn chưa đủ", "Hẹn bản đủ sau khi có nguồn"),
("Cùng đồng nghiệp sửa có nguồn", "Đề nghị kiểm lại bước nhập"),
("Yêu cầu xác nhận đúng người", "Chuyển người có quyền duyệt"),
("Ghi nghi vấn, chuyển kiểm tra", "Yêu cầu nguồn độc lập để đối chiếu"),
("Ghi điều chỉnh, không sửa khớp giả", "Chuyển chị Vân kiểm chứng"),
("Xin chủ nguồn xác nhận", "Giữ cả hai bản ở trạng thái chờ"),
("Kiểm quyền trước khi chia sẻ", "Chuyển người phê duyệt"),
("Đóng tài liệu trước khi quay", "Chỉ khu quay không có hồ sơ riêng"),
("Tạo bản điều chỉnh mới", "Giữ bản cũ và xin xác nhận thay đổi"),
("So mã và nội dung hồ sơ", "Trả tệp cho đúng người phụ trách"),
("Ưu tiên theo hạn và nguồn đủ", "Bàn giao phần đang chờ"),
("Kiểm kết quả trước khi thử lại", "Giữ nháp và đối chiếu lịch sử"),
("Giải thích đơn vị và số nguồn", "Đổi sang bảng đối chiếu dễ đọc"),
("Cho Huy thử, giải thích bước sai", "Cùng làm một ví dụ nhỏ"),
("Trình bày bản đối chiếu có nguồn", "Mời mọi người cùng kiểm kỳ"),
],
"CS":[
("Kiểm trạng thái rồi trả lời", "Hỏi rõ mục tiêu khách trước"),
("Mở kiểm tra chặng, hẹn cập nhật", "Bàn giao đầu mối theo dõi"),
("Đề nghị gửi bù phần thiếu", "Đề nghị hoàn phần thiếu theo chính sách"),
("Mở yêu cầu đổi đúng mã", "Xin phương án phù hợp đã được duyệt"),
("Mở đối soát chứng cứ giao", "Nhờ Ngọc kiểm địa điểm nhận"),
("Kiểm giai đoạn và đề nghị hủy", "Trao đổi phương án còn khả dụng"),
("Thu thập chứng cứ đúng phạm vi", "Chuyển đầu mối chuyên trách"),
("Kiểm nhật ký thực thi lệnh hoàn", "Nhờ trưởng ca kiểm kết quả"),
("Xác nhận vấn đề, hỏi ngắn gọn", "Đặt ranh giới và chuyển trưởng ca"),
("Kiểm quyền từng người hỏi", "Giữ thông tin, chuyển xác minh"),
("Gộp yêu cầu sau khi đối chiếu", "Gán một đầu mối và giữ lịch sử"),
("Bàn giao cả lời hẹn và chứng cứ", "Giữ vụ tới khi người nhận xác nhận"),
("Hỗ trợ vấn đề thật, không mua sao", "Giải thích riêng về chính sách"),
("Phản hồi công khai ngắn, mời nhắn riêng", "Xác minh vụ gốc trước khi phản hồi"),
("Kiểm quyền, không tin tên hiển thị", "Chuyển xác minh cho trưởng ca"),
("Xin duyệt ngoại lệ trước khi hứa", "Đề nghị phương án đang hợp lệ"),
("Giữ hai nguồn, xin chứng cứ bổ sung", "Mở đối soát với kho"),
("Nhận thiếu sót, làm bước còn lại", "Thông báo mốc mới và ghi hạn cũ"),
("Nhận lỗi và gửi lại đúng ngữ cảnh", "Nhờ trưởng ca hỗ trợ khắc phục"),
("Giữ nháp, hẹn kiểm tra lại", "Chuyển đầu mối tra cứu khác"),
("Hướng dẫn đúng bước trong ứng dụng", "Hỏi khách thử và xác nhận kết quả"),
("Cảm ơn, nhắc đúng vụ đã xử lý", "Lắng nghe góp ý tiếp theo"),
("Nhận hẹn và phân loại yêu cầu", "Chia việc, tạm giới hạn nhận mới"),
("Nhóm nguyên nhân theo hồ sơ", "Đề nghị cải tiến bước đóng gói"),
]}

SPECIAL = {
"MB-E05":dict(opening="An: ‘Hình như trên kệ thiếu một chú thỏ… mình kiểm lại trước nhé?’",fact="Nhật ký chuyển kệ cho thấy An đặt chú thỏ sang bàn gói quà. Chưa có hàng bị lấy khỏi tiệm.",observation="Vị trí cũ trống nhưng cửa vẫn mở và chưa đối chiếu các bàn.",station="shelf"),
"MB-E06":dict(opening="Một món hàng vừa được mang qua quầy nhưng chưa có giao dịch tương ứng.",fact="Biên bản xác nhận mã hàng đã đi qua lối ra, quầy chưa có thanh toán; vẫn cần nhắc hoặc nhờ hỗ trợ, không truy đuổi.",observation="Có món rời kệ. Chỉ việc thiếu ở kệ chưa đủ kết luận.",station="counter"),
"MB-E07":dict(opening="Bảo: ‘Mình quay clip về tiệm nhé? Bạn tài trợ cho mình một set quà được không?’",fact="Bảo đang đề nghị hợp tác, chưa có thỏa thuận tài trợ. Không có nghĩa vụ tặng hoặc bảo đảm bài đăng tích cực.",observation="Bảo đứng ở góc trưng bày, một khách đang chờ xem sản phẩm.",station="counter",npc=5,costs=[0,20]),
"MB-E08":dict(opening="Một vị khách né camera: ‘Mình không muốn xuất hiện trong clip…’",fact="Máy quay đang hướng vào khách chưa đồng ý. Tiệm có thể chỉ khu quay riêng hoặc yêu cầu dừng.",observation="Bảo có thể di chuyển sang góc trưng bày; không cần đóng cả tiệm.",station="counter",npc=5),
"MB-E11":dict(opening="Một khách quay lại khay dùng thử: ‘Cho mình thêm phần nữa nhé?’",fact="Trong lượt này khách đã nhận hai phần dùng thử. Chưa có món mua; điều đó không chứng minh họ sẽ không mua sau này.",observation="Tiệm còn phần dùng thử; chủ tiệm được chọn giới hạn rõ ràng hoặc mời thêm.",station="shelf",costs=[0,5]),
"MB-E12":dict(opening="Khách: ‘Mình đang tìm món nhỏ hơn, số xu mang theo hơi ít.’",fact="Khách đã nói rõ ngân sách thấp. Giúp đỡ hay từ chối nhẹ nhàng đều là lựa chọn hợp lý.",costs=[15,0]),
"MB-E13":dict(opening="Khách tìm trong túi: ‘Mình để quên ví rồi. Có thể để gói này lại không?’",fact="Gói vẫn ở quầy, chưa thanh toán và chưa giao. Không ghi doanh thu khi giữ chờ.",costs=[0,10]),
"MB-E02":dict(opening="Một tin nhắn về đơn từ ca bàn giao: ‘Gói của mình còn thiếu một món nhỏ.’",fact="Biên bản ca bàn giao ghi thiếu một món. Đây là đơn của ca trước, không phải đơn bạn đã đóng.",costs=[8,15]),
"MB-E20":dict(opening="Có một chiếc túi dưới ghế. Bác Tư đã rời tiệm một lúc.",fact="Trong túi có móc khóa hình lá, người quay lại phải mô tả đúng dấu hiệu này; không đăng đồ riêng lên bảng tin.",station="counter",npc=2),
"MB-E21":dict(opening="Một vị khách trước cửa vừa bị giật túi, đang rất hoảng.",fact="Bạn chỉ có dữ kiện quan sát tại chỗ. Bảo vệ khu phố có thể nhận vụ. Không truy đuổi hay xô xát.",observation="Khách cần được trấn an; vật sưu tầm và tiền tiết kiệm của bạn không bị mất.",station="door"),
"MB-E24":dict(opening="Bác Tư: ‘Cuối ngày mình cùng học gói quà ở góc tiệm được không?’",fact="Đây là hoạt động nhỏ tự chọn. Có thể dùng vật liệu tiệm hoặc cùng góp, không cần đạt doanh số.",npc=2,costs=[15,0]),
"PH-E19":dict(fact="Nhật ký chuyển cho thấy hộp được đưa sang khu tạm giữ. Chưa có bằng chứng khách lấy hàng.",station="shelf"),
"PH-E09":dict(opening="Một khách hỏi điều nằm ngoài phiếu.",fact="Quầy không chẩn đoán hay hướng dẫn cách dùng thuốc. Chuyển người phụ trách là cách xử lý đúng.",npc=1),
"AC-E14":dict(opening="‘Số đang lệch, sửa cho khớp trước được không?’ — một đề nghị cần làm rõ.",fact="Chưa có chứng từ giải thích chênh lệch. Sửa số cho đẹp không tạo ra nguồn hợp lệ; có thể giữ chờ hoặc chuyển chị Vân.",npc=2,station="workbench"),
"CS-E18":dict(opening="Một vụ trong ca bàn giao đã lỡ mốc cập nhật. Bạn đang tiếp nhận phần còn lại.",fact="Lời hẹn cũ thuộc hồ sơ ca bàn giao, cần được giữ trong lịch sử. Không coi đó là lời hẹn bạn chưa từng đưa ra.",station="workbench"),
}

SCRIPTS={}
for seed in EVENT_SEEDS:
    prefix=seed["id"].split("-")[0]
    number=int(seed["id"].split("E")[1])
    labels=CHOICES[prefix][number-1]
    special=SPECIAL.get(seed["id"],{})
    # Set up a real, explicitly fictional incident instance rather than fabricate player history.
    fact=special.get("fact",seed["truth"].replace("người chơi", "ca trước").replace("Người chơi", "Ca trước"))
    costs=special.get("costs",[0,0])
    npc=special.get("npc",5 if "clip" in seed["title"].lower() else 2 if prefix in ["MB","PH"] else 1)
    default_stage={"MB":"counter","PH":"workbench","AC":"workbench","CS":"workbench"}[prefix]
    script=dict(id=seed["id"],career=seed["career_id"],title=seed["title"],category=seed["category"],min_day=seed["min_game_day"],
        npc=f'{seed["career_id"]}_npc_{npc:02d}',station=special.get("station",default_stage),
        opening=special.get("opening",f'Có chuyện cần bạn xem: {seed["title"].lower()}. Mình cùng kiểm tra rồi chọn cách xử lý nhé.'),
        evidence=[dict(id="observe",title="Điều đang thấy",source="Quan sát tại cảnh",text=special.get("observation",f'Tình huống mới: {seed["title"]}. Chưa đưa ra kết luận trước khi kiểm hồ sơ.')),
                  dict(id="record",title="Đối chiếu dữ kiện",source="Hồ sơ sự kiện",text=fact)],
        options=[dict(id="a",label=labels[0],cost=costs[0],requires=["observe","record"],response=f"Mình thống nhất bước này nhé: {labels[0].lower()}.",
                      steps=["Chuẩn bị theo dữ kiện đã kiểm",labels[0]],follow_up=seed["follow_up"]),
                 dict(id="b",label=labels[1],cost=costs[1],requires=["observe","record"],response=f"Được, mình theo phương án: {labels[1].lower()}.",
                      steps=["Xác nhận phương án với người liên quan",labels[1]],follow_up="Mọi người đã nhận được cập nhật về phương án đã thực hiện. " + seed["follow_up"])],
        original_seed=seed["id"],follow_up=seed["follow_up"])
    SCRIPTS[seed["id"]]=script

# Force narrative follow-ups to describe actions that the runtime actually carried out.
SCRIPTS["MB-E07"]["options"][0]["follow_up"]="Bảo: ‘Tiệm chưa nhận tài trợ, nhưng vẫn cho mình xem khu trưng bày. Lần sau mình sẽ hỏi hợp tác trước.’"
SCRIPTS["MB-E07"]["options"][1]["follow_up"]="Bảo: ‘Mình đã nhận phần quà được tiệm tài trợ. Đây là trải nghiệm hợp tác, không phải đánh giá mua hàng độc lập.’"
SCRIPTS["MB-E05"]["options"][0]["follow_up"]="An đã đặt món về đúng vị trí. Không có ai bị kết tội từ việc kệ trống."
SCRIPTS["MB-E05"]["options"][1]["follow_up"]=SCRIPTS["MB-E05"]["options"][0]["follow_up"]
SCRIPTS["MB-E11"]["options"][0]["follow_up"]="Khách đã biết giới hạn phần dùng thử của tiệm. Chưa có đơn mua nào được ghi nhận."
SCRIPTS["MB-E11"]["options"][1]["follow_up"]="Khách nhận phần thử thêm. Không tự phát sinh doanh thu hoặc lời hứa mua hàng."


def instantiate(event_id: str, serial: int, day: int, practice: bool=False) -> dict:
    script=SCRIPTS[event_id]
    return dict(id=f'{event_id}-{day}-{serial}',script=event_id,npc=script["npc"],title=script["title"],stage="noticed",read=[],
        chosen=None,step=0,practice=practice,created_day=day,created_turn=serial,cost_paid=0,completion_log=None)


def event_view(event: dict|None) -> dict|None:
    if not event: return None
    s=SCRIPTS[event["script"]]
    v=tree_copy(event)
    v.update(opening=s["opening"],category=s["category"],station=s["station"],options=s["options"])
    v["evidence"]=[dict(e, text=e["text"] if e["id"] in event["read"] else None) for e in s["evidence"]]
    if event["stage"]!="resolved":
        v["options"]=[{k:val for k,val in o.items() if k!="follow_up"} for o in v["options"]]
    return v
