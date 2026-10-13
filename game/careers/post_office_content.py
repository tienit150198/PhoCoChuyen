"""Fictional Cánh Thư parcels and the game's own tariff board."""
PEOPLE = [
    ('Cô Thư', 'Trưởng quầy', 'Giữ từng dấu nhận và từng lời hẹn.', 'warm'),
    ('Anh Lộc', 'Người bán sách', 'Gói sách cho bạn đọc khắp phố.', 'quiet'),
    ('Mai', 'Sinh viên', 'Có bộ hồ sơ cần gửi đúng hạn.', 'genz'),
    ('Chú Bình', 'Thợ gốm', 'Mỗi chiếc cốc đều được nặn bằng tay.', 'picky'),
    ('Cô Hạnh', 'Khách nhận hàng', 'Luôn đem theo phiếu hẹn và giấy nhận.', 'warm'),
    ('Anh Vũ', 'Nhân viên tuyến', 'Chỉ nhận túi thư có bảng kê đủ mã.', 'quiet'),
]

# id, unlock, kind, item, title, opening, deadline, receipt, packaging
SCENARIOS = [
    ('books', 1, 'send', 'Sách truyện', 'Sách cho thư viện nhỏ', 'Anh Lộc gửi sách tặng thư viện; đến trong bốn ngày là được.', 4, False, 'box'),
    ('cards', 1, 'send', 'Thiệp giấy', 'Thiệp sinh nhật', 'Mai muốn thiệp giữ phẳng, không bị gập góc.', 4, False, 'flat'),
    ('seeds', 1, 'send', 'Gói hạt giống khô', 'Hạt giống cho vườn trường', 'Gói hạt khô đã kín, cần thêm hộp để không bị ép.', 4, False, 'box'),
    ('toy', 1, 'send', 'Thú bông', 'Món quà mềm', 'Khách gửi thú bông, nhãn cũ thiếu số nhà; phiếu đã bổ sung bên cạnh.', 4, False, 'box'),
    ('scholarship', 4, 'registered', 'Hồ sơ học bổng', 'Lá thư có dấu nhận', 'Mai cần mã theo dõi và chữ ký người nhận, hạn bốn ngày.', 4, True, 'flat'),
    ('notice', 4, 'registered', 'Thư mời triển lãm', 'Lời mời cần hồi báo', 'Cô Thư dặn lưu mã thư và bằng chứng người nhận đã ký.', 4, True, 'flat'),
    ('urgent', 4, 'registered', 'Bản in lịch diễn', 'Kịp buổi diễn ngày mai', 'Bản in phải đến ngày mai và có chữ ký xác nhận.', 1, True, 'flat'),
    ('cup', 10, 'fragile', 'Cốc gốm', 'Chiếc cốc đầu tay', 'Chú Bình sợ quai cốc vỡ; cần chèn chống xê dịch và nhãn dễ vỡ.', 4, False, 'cushion'),
    ('glass', 10, 'fragile', 'Lọ thủy tinh rỗng', 'Lọ hoa trong suốt', 'Lọ rỗng nhưng vẫn giòn; khách cần nhận ngay ngày mai.', 1, False, 'cushion'),
    ('map', 10, 'fragile', 'Bản đồ cuộn', 'Bản đồ khổ dài', 'Cuộn bản đồ dài hơn 60 cm, cần ống cứng có hai nắp.', 4, False, 'tube'),
    ('collect', 20, 'collection', 'Hộp khăn', 'Nhận tại quầy', 'Cô Hạnh mang giấy nhận; so đúng họ tên, mã kiện rồi mới trao.', 4, False, 'box'),
    ('mismatch', 20, 'collection', 'Hộp tranh nhỏ', 'Tên người nhận không khớp', 'Người đến nhận nói là hàng của mình, nhưng giấy có tên khác phiếu.', 4, False, 'box'),
    ('return_away', 20, 'return', 'Hộp đồ chơi', 'Người nhận đã chuyển đi', 'Tuyến giao ghi không tìm thấy người nhận; hoàn về địa chỉ người gửi đã xác minh.', 4, False, 'box'),
    ('return_address', 20, 'return', 'Bộ ảnh', 'Trả lại thư sai địa chỉ', 'Phiếu hoàn ghi địa chỉ không tồn tại. Không sửa hồ sơ thành giao thành công.', 4, True, 'flat'),
    ('market_batch', 40, 'batch', 'Quà phiên chợ', 'Ba kiện, ba tuyến', 'Anh Vũ chờ túi thư cuối ca. Kiểm từng mã; các kiện không đi chung một tuyến.', 4, False, 'box'),
    ('return_batch', 40, 'batch', 'Hàng hoàn cuối tuyến', 'Túi hàng hoàn', 'Ba kiện hoàn có ba người gửi khác nhau. Đối chiếu từng địa chỉ và lưu từng phiếu hoàn.', 4, False, 'box'),
    ('festival_batch', 40, 'batch', 'Thiệp và quà lễ hội', 'Túi thư ngày hội', 'Trong túi có một kiện dễ vỡ, một thư cần ký và một gói gấp. Không dùng chung một dịch vụ.', 4, True, 'flat'),
]

ZONES = [('local', 'Nội phố', 6, 'A'), ('near', 'Vùng gần', 10, 'B'), ('far', 'Vùng xa', 14, 'C')]
SERVICES = [('standard', 'Thường · 4 ngày', 0), ('registered', 'Bảo đảm · 4 ngày, ký nhận', 4),
            ('express', 'Nhanh · 1 ngày, ký nhận', 8), ('stored', 'Nhận tại quầy · đã trả cước', 0),
            ('return', 'Hoàn về người gửi · không thu thêm', 0)]
PACKS = [('box', 'Hộp vừa, chèn kín khoảng trống'), ('flat', 'Bìa cứng giữ phẳng, bọc kín'),
         ('cushion', 'Bọc đệm, chèn riêng, dán nhãn dễ vỡ'), ('tube', 'Ống cứng, khóa hai đầu'),
         ('bare', 'Dán nhãn trực tiếp, không bọc')]
MILESTONES = [
    dict(id='counter', label='Quầy thư tin cậy', jobs=18, days=6, advanced=0),
    dict(id='routes', label='Người giữ đúng lời hẹn', jobs=65, days=20, advanced=0),
    dict(id='master', label='Cánh thư của cả phố', jobs=180, days=45, advanced=12),
]
NOTEBOOK = [
    'Đây là bảng cước và quy tắc hư cấu chỉ dùng trong trò chơi.',
    'Cước = giá vùng + 3 xu × số khối 500 g làm tròn lên + phụ phí dịch vụ + 5 xu nếu cạnh dài nhất trên 60 cm.',
    'Thường: 4 ngày. Bảo đảm: 4 ngày, có ký nhận. Nhanh: 1 ngày, có ký nhận. Chọn dịch vụ rẻ nhất đáp ứng yêu cầu.',
    'Nhận tại quầy và hàng hoàn đã thanh toán cước: ghi 0 xu, không thu lần nữa.',
    'So tên trên giấy với phiếu. Không khớp thì giữ kiện xác minh, không giao cho người tự xưng.',
    'Nhãn thiếu địa chỉ thì dùng phiếu bổ sung đã xác minh. Hàng hoàn đổi nhãn về người gửi.',
    'Cân đọc số thực tế, không chép khối lượng khách ước tính. Cạnh dài trên 60 cm có phụ phí dù kiện nhẹ.',
    'Nội phố → A; vùng gần → B; vùng xa → C. Người đến nhận → quầy; chưa đúng danh tính → kệ giữ.',
    'Túi gửi đi cần bảng kê ký bàn giao. Nhận tại quầy cần chữ ký người nhận. Hoàn cần phiếu hoàn; giữ xác minh cần phiếu hẹn.',
    'Cước thuộc bưu điện. Lương trả theo hợp đồng khi khép ca; thưởng chất lượng chỉ 4–9 xu mỗi việc.',
]
