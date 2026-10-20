"""Immutable eight-stage management catalogue, independent of game state/docs.

``profile`` and ``stage`` return frozen dataclasses; ``profile_dict`` and
``stage_dict`` return detached JSON-ready dictionaries. ``quote`` returns a
detached integer-xu ledger. Demand is an integer percentage of sold volume,
not the acceptance score. Fees are incremental final prices, never indexed.
Resources and target income are TOTALS across the coordinated sites.

Business costs use exact rational arithmetic, 60% variable / 40% fixed wages.
Revenue rounds up, net rounds to nearest xu (ties up); cost remainders are
distributed by largest fraction so every displayed receipt reconciles exactly.
Agency revenue is the personal allowance only: organizational budgets never
enter this ledger. Community work has no cash revenue, costs, fee or allowance.
"""
from dataclasses import asdict, dataclass
from fractions import Fraction
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class Stage:
    tier: int
    title: str
    fee: int
    sites: int
    resources: int
    net: int
    days: int
    clean: int


@dataclass(frozen=True)
class Material:
    code: str
    name: str
    unit: str
    bundle: str
    quality: str
    unit_cost: int
    batch_units: int
    service_name: str
    service_unit: str


@dataclass(frozen=True)
class Choice:
    id: str
    label: str
    evidence: str
    score: int


@dataclass(frozen=True)
class Scenario:
    title: str
    planning: tuple[Choice, ...]
    allocation: tuple[Choice, ...]
    exception: tuple[Choice, ...]
    acceptance: tuple[Choice, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class Profile:
    cid: str
    kind: str
    group: str
    resource_name: str
    roles: tuple[str, ...]
    materials: tuple[Material, ...]
    stages: tuple[Stage, ...]
    scenario: Scenario
    focus: str


_FEES = (50_000, 250_000, 1_000_000, 4_000_000, 12_000_000, 35_000_000, 100_000_000, 250_000_000)
_NET = (1000, 3500, 12000, 35000, 90000, 200000, 420000, 800000)
_SITES = (1, 1, 1, 2, 3, 5, 8, 12)
_RESOURCES = (2, 4, 6, 10, 16, 24, 36, 50)
_DAYS = (2, 7, 14, 30, 60, 100, 160, 240)
_CLEAN = (10, 30, 70, 140, 260, 450, 750, 1200)
# factor in tenths; material, wage, premises, loss, turnover-tax percentages.
_GROUPS = MappingProxyType({
    'retail': (10, 70, 8, 4, 2, 4),
    'food': (8, 55, 18, 8, 3, 4),
    'service': (7, 35, 25, 12, 3, 4),
    'technical': (12, 50, 20, 10, 3, 4),
    'farm': (12, 50, 18, 12, 4, 4),
    'hospitality': (15, 25, 30, 20, 3, 4),
    'professional': (6, 20, 35, 12, 2, 4),
    'arts': (8, 40, 25, 12, 3, 4),
    'logistics': (12, 55, 20, 10, 3, 4),
    'agency': (0, 0, 0, 0, 0, 0),
    'community': (0, 0, 0, 0, 0, 0),
})

# Each authored row: career | roles | material/service name | unit | bundle |
# quality | planning pair | allocation pair | exception pair | acceptance pair |
# four phase-specific evidence records. A pair is full / incomplete handling.
_AUTHORED = '''mother_baby|tư vấn tuổi;kiểm lô|Bộ chăm bé theo tuổi|bộ|Tã đúng cỡ, khăn và đồ vệ sinh cho một bé; tách mã từng món|Đúng độ tuổi, nguyên niêm phong và còn hạn|Chốt độ tuổi và bảng cỡ trước đặt bộ~Đặt một cỡ cho mọi bé|Chia quầy tư vấn tuổi và bàn kiểm lô~Để tư vấn viên kiêm kiểm lô không đối chiếu|Cách ly lô lỗi, đổi đúng mã cho khách~Đổi sang cỡ gần nhất khi thiếu hàng|Đối chiếu mã lô và người nhận từng bộ~Chỉ đếm tổng túi đã giao|Phiếu tuổi và cỡ;Lịch tư vấn và kiểm lô;Biên bản cách ly lô;Phiếu nhận đủ mã
pharmacy|người phụ trách chuyên môn;kiểm vật tư|Bộ vật tư chăm sóc|bộ|Băng gạc, khẩu trang và vật tư có mã lô; thuốc theo phiếu hợp lệ riêng|Người đủ chuyên môn kiểm phiếu, hạn và điều kiện bảo quản|Lập danh sách vật tư và phiếu cần kiểm chuyên môn~Gộp vật tư với thuốc không kiểm phiếu|Bố trí người phụ trách kiểm phiếu tại mỗi quầy~Giao kiểm phiếu cho người chưa đủ điều kiện|Khóa lô bị thu hồi, truy các điểm đã nhận~Chuyển lô bị thu hồi sang điểm ít khách|Nghiệm thu phiếu và truy xuất đến từng lô~Chỉ so tổng số hộp xuất|Danh sách phiếu và lô;Lịch người phụ trách;Phiếu thu hồi liên điểm;Biên nhận kiểm chuyên môn
accounting|lập sổ;soát xét|Bộ sổ kế toán khách hàng|bộ hồ sơ|Chứng từ một kỳ, bảng đối chiếu và báo cáo bàn giao cho một khách|Đủ chứng từ, cân số dư và được người khác kiểm chéo|Lập lịch khóa sổ theo số chứng từ từng khách~Hẹn mọi khách cùng một giờ khóa sổ|Tách người lập sổ và người kiểm chéo~Để người lập tự duyệt toàn bộ|Treo chứng từ thiếu và xin bổ sung có hạn~Ước số tiền để kịp chốt sổ|So số dư, chứng từ và xác nhận từng khách~Nghiệm thu theo số trang in|Lịch chốt từng khách;Phân công lập và soát;Danh sách chứng từ thiếu;Biên bản đối chiếu số dư
customer_care|tiếp nhận;hỗ trợ chuyên sâu|Gói xử lý yêu cầu|nhóm yêu cầu|Mười yêu cầu có mã, mức ưu tiên, lịch hẹn và xác nhận phản hồi|Không lộ thông tin khách, lời hẹn có người chịu trách nhiệm|Xếp yêu cầu theo hạn hẹn và mức ảnh hưởng~Xếp chỉ theo thứ tự đến|Chia yêu cầu khó cho nhóm chuyên sâu~Chia đều không xét chuyên môn|Báo trễ hẹn và chuyển cấp kèm lịch sử~Đóng yêu cầu để giảm hàng chờ|Kiểm phản hồi khách và lời hẹn đã thực hiện~Chỉ đếm yêu cầu được đóng|Bảng ưu tiên yêu cầu;Lịch nhóm hỗ trợ;Phiếu chuyển cấp;Xác nhận phản hồi khách
teacher|soạn chuyên đề;hỗ trợ lớp|Chuyên đề liên lớp|chuyên đề|Giáo án, học liệu, hoạt động và phiếu phản hồi cho một nhóm lớp|Phù hợp lứa tuổi, không trùng lịch và có hỗ trợ học sinh cần giúp|Chốt mục tiêu học và lịch từng lớp~Dùng cùng bài tập cho mọi trình độ|Ghép giáo viên theo chuyên môn và lớp cần hỗ trợ~Chia số lớp đều không xét chuyên môn|Điều chỉnh học liệu khi lớp chưa theo kịp~Tăng tốc bài mới cho kịp lịch|Xem sản phẩm học tập và phản hồi từng lớp~Chỉ xác nhận đã dạy đủ tiết|Kế hoạch chuyên đề;Lịch giáo viên và lớp;Phiếu điều chỉnh học liệu;Sản phẩm và phản hồi lớp
tour_guide|hướng dẫn đoàn;đặt dịch vụ|Đoàn tham quan|đoàn|Danh sách khách, phương tiện, điểm tham quan và bữa ăn đặt trước|Đủ khách theo danh sách, dịch vụ đúng lịch và nhu cầu hỗ trợ|Chốt lịch trình, sức chứa và suất ăn từng đoàn~Nhận đoàn trước khi xác nhận xe|Giao một hướng dẫn viên đủ điều kiện theo mỗi đoàn~Cho một người dẫn hai đoàn cùng giờ|Báo trễ xe, đổi thứ tự điểm và kiểm người~Cho đoàn tự đi trước rồi tập hợp sau|Đối danh sách khách và phiếu dịch vụ đã dùng~Chỉ kiểm ảnh chụp cuối tour|Lịch trình và xác nhận xe;Lịch hướng dẫn viên;Nhật ký đổi tuyến;Danh sách khách bàn giao
milk_tea|ủ trà;pha chế|Mẻ trà sữa|mẻ|Trà ủ, sữa và topping cân theo công thức cho hai mươi ly|Ghi giờ ủ, hạn topping, độ ngọt và mẫu kiểm vị|Tính mẻ trà theo lịch nhận ly và hạn topping~Ủ hết trà từ đầu ca|Tách trạm ủ và trạm pha theo nhịp đơn~Để một trạm nhận mọi đơn cùng giờ|Cách ly topping quá hạn, pha lại bằng mẻ đạt~Trộn topping cũ với mẻ mới|So số ly, công thức và mẫu kiểm vị từng mẻ~Chỉ đếm cốc đã đóng nắp|Phiếu định lượng mẻ;Lịch trạm ủ và pha;Phiếu loại topping;Mẫu kiểm vị và giao ly
restaurant|bếp nước dùng;bếp ra món|Tiệc mì theo đoàn|bàn tiệc|Mì, nước dùng, rau và đồ ăn kèm định lượng cho mười khách|Đúng cấp cay, tách dị ứng và giữ nóng khi bàn giao|Chốt số khách, cấp cay và thứ tự ra món~Nấu một cấp cay cho mọi bàn|Chia bếp nước dùng và bếp ra món theo giờ tiệc~Dồn cả nấu và giao cho một bếp|Nấu riêng suất có dị ứng và đổi dụng cụ~Gắp nguyên liệu dị ứng ra sau nấu|Kiểm nhiệt, khẩu phần và phiếu bàn tiệc~Chỉ nghiệm thu số bát|Phiếu menu từng bàn;Lịch trạm bếp;Phiếu xử lý dị ứng;Biên nhận bàn tiệc
cafe_bakery|thợ bánh;pha cà phê|Mẻ bánh và đồ uống|khay|Bột, bơ, nhân cho mười bánh kèm lịch pha đồ uống theo đơn|Đúng mẻ nướng, thời gian ra lò và hạn bán trong ngày|Xếp mẻ nướng theo giờ nhận và thời gian ủ~Nướng toàn bộ từ đầu ngày|Đặt lịch lò không chồng mẻ, tách quầy pha~Cho hai mẻ dùng cùng lò cùng lúc|Tách bánh chưa chín, nướng bổ sung và báo giờ mới~Bọc bánh chưa chín giao trước|Kiểm mẫu ruột bánh và đối phiếu giao từng khay~Chỉ kiểm màu vỏ ngoài|Lịch ủ và nướng;Lịch lò và quầy pha;Phiếu mẻ phải làm lại;Phiếu kiểm ruột và giao khay
florist|chọn hoa;trang trí sự kiện|Bộ hoa trang trí|bộ|Hoa tươi, khung cắm và vật liệu tái dùng cho một bàn sự kiện|Đúng tông màu, độ tươi và có phiếu thu hồi khung|Đặt hoa theo giờ sự kiện và thời gian dưỡng~Mua cùng lô cho mọi ngày tiệc|Chia bàn cắm và đội lắp theo địa điểm~Dồn đội lắp vào một điểm dù lịch trùng|Thay cành héo đúng tông, cập nhật vật liệu trả~Che cành héo vào phía trong|So mẫu trang trí và kiểm khung thu hồi~Chỉ đếm bó đã giao|Phiếu hoa và giờ tiệc;Lịch đội cắm và lắp;Phiếu thay cành;Ảnh mẫu và phiếu thu khung
grocery|thu ngân;kiểm kệ|Giỏ hàng gia đình|giỏ|Gạo, mì, dầu và đồ vệ sinh thành giỏ có số lượng từng mã|Cân đủ, đúng nhãn giá, còn hạn và truy được lô|Đặt giỏ theo dự báo từng điểm và hạn dùng~Nhập cùng số lượng cho mọi điểm|Chia thu ngân và kiểm kệ, giữ người mỗi điểm~Dồn thu ngân vào một điểm bỏ điểm còn lại|Cách ly lô mất lạnh, điều lô đạt kèm giá vốn~Chuyển lô mất lạnh sang điểm khác bán|Đối phiếu xuất, hóa đơn và tồn theo lô~Nghiệm thu chỉ theo tiền thu ngân|Dự toán giỏ theo điểm;Lịch thu ngân và kiểm kệ;Phiếu điều chuyển có giá vốn;Đối soát hóa đơn và tồn lô
repair|chẩn đoán;thợ sửa|Gói bảo dưỡng thiết bị|thiết bị|Kiểm lỗi, linh kiện đúng mã, công sửa và phiếu bảo hành một máy|Có kết quả kiểm sau sửa, số máy và linh kiện truy xuất được|Chẩn đoán rồi chốt linh kiện và thời hạn~Đặt linh kiện trước khi kiểm lỗi|Xếp bàn sửa theo tay nghề và lịch thiết bị đo~Cho hai máy chiếm cùng bàn sửa|Dừng lắp linh kiện sai mã, xin thay đúng mã~Lắp linh kiện gần giống để kịp giao|Chạy kiểm sau sửa và giao phiếu bảo hành~Chỉ bật nguồn thấy sáng là giao|Phiếu chẩn đoán và mã máy;Lịch bàn và thợ;Phiếu đổi linh kiện;Kết quả kiểm và bảo hành
farm|chăm khu trồng;kiểm thu hoạch|Lô nông sản|lô|Giống, vật tư chăm cây và công thu hoạch một khu có mã truy xuất|Theo lịch mùa vụ, ghi vật tư và phân loại đạt chuẩn đầu ra|Lập lịch gieo và đầu ra theo từng khu~Gieo đồng loạt không xét lịch nhận|Chia tổ chăm và tổ thu, đặt lịch máy theo khu~Đặt một máy ở hai khu cùng giờ|Tách lô chất lượng kém, điều lịch giao lô đạt~Trộn lô kém với lô tốt|Đối sản lượng, mã khu và nhật ký vật tư~Chỉ cân tổng không ghi nguồn|Lịch mùa vụ và hợp đồng;Lịch tổ và máy;Phiếu tách lô;Biên nhận cân và truy xuất
delivery|phân tuyến;tài xế|Chuyến giao nhiều kiện|chuyến|Mười kiện, phiếu tuyến, nhiên liệu và xác nhận nhận hàng từng điểm|Không quá tải, đúng hạn; COD là tiền giữ hộ được đối soát riêng|Chốt tuyến theo hạn giao, tải xe và COD~Chọn tuyến ngắn nhất bỏ hạn giao|Giao xe và tài xế theo tải, khóa lịch chuyến~Xếp một xe vào hai chuyến cùng giờ|Lập phiếu giao lại khi khách vắng, giữ nguyên COD~Ghi đã giao dù khách chưa nhận|Đối kiện, chữ ký và sổ COD riêng~Cộng COD vào doanh thu giao hàng|Bảng tuyến và tải xe;Lịch xe và tài xế;Phiếu giao lại;Biên nhận và sổ COD
homestay|buồng phòng;lễ tân|Phòng đêm kèm dọn|phòng đêm|Một phòng theo lịch đặt, bộ khăn sạch, vệ sinh và nhận trả phòng|Phòng đạt vệ sinh, không đặt trùng và bảo trì trước nhận khách|Chốt lịch đặt và khoảng dọn giữa hai lượt~Nhận trùng phòng khi giờ đến khác nhau|Giao buồng phòng theo giờ trả và lễ tân theo giờ nhận~Xếp dọn sau giờ khách đến|Khóa phòng hỏng, chuyển khách sang phòng đạt~Bỏ qua lỗi khóa phòng để đủ công suất|Kiểm tình trạng phòng và biên bản nhận trả~Chỉ đếm số phòng đã thu tiền|Lịch phòng và giờ dọn;Lịch buồng phòng và lễ tân;Phiếu khóa phòng sửa;Biên bản nhận trả phòng
pet_care|chăm thú;giám sát lưu trú|Ca chăm thú|thú một ca|Ô lưu trú, thức ăn theo chủ dặn, vệ sinh và nhật ký một thú|Tách nhu cầu từng thú, không quá tải người chăm|Ghi khẩu phần, thói quen và người đón từng thú~Dùng một khẩu phần cho mọi thú|Xếp ô và người chăm theo tính tương thích~Ghép thú lạ chung ô cho đủ chỗ|Tách thú có dấu hiệu bất thường và báo chủ~Giữ chung ô chờ hết ca|Đối nhật ký ăn nghỉ và xác nhận đúng người đón~Chỉ đếm số thú đã trả|Phiếu khẩu phần và người đón;Lịch ô và người chăm;Nhật ký báo chủ;Biên bản giao thú
salon|thợ cắt;thợ màu|Lịch tóc theo mẫu|khách|Tư vấn mẫu, vật tư định lượng, ghế và thời gian thợ cho một khách|Mẫu được khách xác nhận, kiểm sản phẩm và chất lượng tóc|Chốt mẫu và thời lượng trước giữ ghế~Nhận mọi mẫu với cùng thời lượng|Xếp thợ màu và thợ cắt đúng lịch ghế~Đặt hai khách nhuộm cùng ghế|Dừng sản phẩm không phù hợp, tư vấn phương án mới~Dùng tiếp để kịp khách kế tiếp|So mẫu đã duyệt và phản hồi khách trước bàn giao~Chỉ chụp ảnh tổng thể rồi kết thúc|Phiếu mẫu và thời lượng;Lịch ghế và tay nghề;Phiếu đổi sản phẩm;Xác nhận mẫu hoàn thành
corp_accounting|lập sổ đơn vị;kiểm khóa sổ|Kỳ khóa sổ đơn vị|kỳ|Bộ chứng từ, bảng số dư và đối chiếu công nợ của một đơn vị|Khóa đúng kỳ, lưu vết điều chỉnh và kiểm chéo trước chốt|Chốt mốc nhận chứng từ theo từng đơn vị~Khóa sổ trước hạn nộp chứng từ|Tách lập sổ với đối chiếu công nợ~Cho người nhập tự phê duyệt sai lệch|Mở phiếu điều chỉnh lệch công nợ có người duyệt~Bù số vào tài khoản khác cho cân|Đối số dư và chữ ký soát xét từng đơn vị~Chỉ kiểm tổng tài sản cân|Lịch khóa sổ;Phân công lập và đối chiếu;Phiếu điều chỉnh;Biên bản soát xét kỳ
tax_payroll|lập lương;soát hồ sơ thuế|Kỳ thuế và lương|khách một kỳ|Bảng công, phụ cấp, khấu trừ và bộ hồ sơ kê khai của một khách|Bảo mật theo khách, đối chiếu đủ người và đúng kỳ|Chốt lịch nhận bảng công và hạn kê khai~Lấy bảng công kỳ trước để lập nhanh|Tách người tính lương và người soát khấu trừ~Gửi mọi bảng lương cho cả nhóm khách|Giữ dòng thiếu căn cứ, yêu cầu xác nhận trước chốt~Ước khoản khấu trừ khi chưa đủ hồ sơ|Đối bảng công, bảng lương và xác nhận khách~Chỉ kiểm tổng tiền chuyển|Lịch chốt công và kê khai;Danh sách quyền xem;Phiếu bổ sung căn cứ;Biên bản đối chiếu lương
group_accounting|hợp nhất;soát nội bộ|Bộ báo cáo hợp nhất|nhóm đơn vị|Báo cáo công ty thành viên, bảng giao dịch nội bộ và bút toán loại trừ|Cùng kỳ báo cáo, cùng phạm vi và có đối chiếu hai bên|Chốt phạm vi đơn vị và thời điểm báo cáo~Gộp báo cáo khác kỳ cho đủ số|Chia nhóm chuẩn hóa và nhóm đối chiếu nội bộ~Để mỗi bên tự xác nhận giao dịch|Treo chênh lệch nội bộ, yêu cầu hai bên đối chiếu~Loại trừ bằng số bình quân|So bút toán loại trừ và dấu vết số nguồn~Chỉ kiểm tổng báo cáo cuối|Bảng phạm vi hợp nhất;Lịch nhóm chuẩn hóa;Biên bản chênh nội bộ;Bảng loại trừ có số nguồn
clothing|tư vấn cỡ;kiểm mẫu|Bộ trang phục theo cỡ|bộ|Áo, quần và phụ kiện có mã mẫu, màu, cỡ cho một khách|Đúng bảng cỡ, nhãn mẫu và điều kiện đổi trả liên điểm|Dự báo cỡ màu theo khách từng điểm~Nhập số lượng đều cho mọi cỡ|Chia quầy tư vấn và phòng thử theo lịch~Giữ một phòng thử cho nhiều khách cùng lúc|Điều chuyển đúng mã cỡ kèm giá vốn~Đổi sang cỡ gần nhất không hỏi khách|So mã mẫu cỡ và phiếu đổi trả~Chỉ đếm túi quần áo|Bảng mẫu cỡ theo điểm;Lịch quầy và phòng thử;Phiếu chuyển đúng mã;Phiếu khách nhận và đổi trả
pet_shop|tư vấn loài;kiểm thức ăn|Bộ đồ dùng thú cưng|bộ|Thức ăn, đồ chơi và vật dụng theo loài và kích cỡ một thú|Thức ăn đúng loài, nguyên niêm và truy được hạn lô|Chọn danh mục theo loài và lịch dùng thức ăn~Nhập một loại thức ăn cho mọi thú|Tách tư vấn loài với kiểm hạn lô~Cho quầy bán bỏ qua kiểm hạn|Khóa lô thức ăn có cảnh báo, truy phiếu bán~Giảm giá lô có cảnh báo để hết tồn|So loài, cỡ và mã lô trên biên nhận~Chỉ kiểm đủ số món trong túi|Danh mục theo loài;Lịch tư vấn và kiểm lô;Phiếu khóa và truy lô;Biên nhận đúng loài cỡ
tra_da|pha mẻ;phục vụ bàn|Mẻ giải khát|bình|Trà, nước sạch, đá và cốc cho hai mươi phần phục vụ|Bình sạch, ghi giờ pha và dụng cụ tách khu bẩn|Pha theo lượng khách và giờ thay bình~Pha một bình dùng xuyên ngày|Chia trạm pha và người tiếp bình theo khu~Bỏ trống trạm rửa khi đông khách|Thay bình nhiễm bẩn và vệ sinh trạm~Châm trà mới vào bình bẩn|Đối giờ pha, vệ sinh cốc và số phần~Chỉ đếm số cốc đã thu tiền|Lịch pha và thay bình;Lịch phục vụ và rửa;Phiếu thay bình;Kiểm cốc và số phần giao
fruit|chọn độ chín;cân đóng giỏ|Giỏ trái cây|giỏ|Trái cây theo khối lượng, khay bảo vệ và phiếu nguồn lô|Đúng độ chín giao hẹn, đủ cân và không dập|Chọn lô theo ngày giao và độ chín~Chọn cùng độ chín cho mọi ngày giao|Tách quầy cân và bàn đóng giỏ theo đơn~Dồn tất cả lên một cân cùng lúc|Tách quả dập, thay lô đạt và ghi hao hụt~Xếp quả dập dưới đáy giỏ|Cân kiểm và đối mã lô từng giỏ~Chỉ nhìn mẫu giỏ bên ngoài|Lịch giao và độ chín;Lịch cân và đóng giỏ;Phiếu loại quả dập;Biên nhận cân và lô
garbage|thu gom;phân loại|Tuyến vệ sinh|tuyến|Xe, dụng cụ bảo hộ, bao phân loại và danh sách điểm thu gom|Không bỏ sót điểm, không trộn nhóm rác và có biên nhận nơi tiếp nhận|Lập tuyến theo lượng rác và giờ tiếp nhận~Chọn tuyến ngắn bỏ điểm xa|Giao xe và tổ theo tải, tách người phân loại~Cho xe quá tải để giảm lượt|Khoanh điểm rác sai loại và báo đội phù hợp~Trộn rác sai loại vào xe chung|Đối từng điểm và phiếu cân nơi tiếp nhận~Chỉ kiểm ảnh xe trống|Bảng tuyến và tải;Lịch xe và phân loại;Phiếu điểm cần xử lý;Phiếu tiếp nhận theo tuyến
drain|khảo sát;vận hành thiết bị|Gói xử lý thoát nước|điểm|Khảo sát, thiết bị phù hợp, vật tư và kiểm dòng chảy một điểm|Khoanh vùng, đủ điều kiện an toàn và ghi kiểm sau xử lý|Khảo sát tuyến ống và lập phương án an toàn~Chọn thiết bị trước khi khảo sát|Giao đội đủ điều kiện và khóa lịch thiết bị~Gửi một thiết bị đến hai điểm cùng giờ|Dừng khi điều kiện không an toàn, khoanh vùng báo phụ trách~Tiếp tục cho kịp giờ nghiệm thu|Kiểm dòng chảy và bàn giao hiện trường sạch~Chỉ xác nhận máy đã chạy|Phiếu khảo sát và phương án;Lịch đội và thiết bị;Biên bản dừng an toàn;Phiếu thử dòng và bàn giao
homemaker|chăm nhà;sắp xếp đồ|Ca hỗ trợ gia đình|nhà một ca|Danh sách việc nhà, vật tư phù hợp và kiểm tài sản trước sau|Làm đúng phạm vi chủ nhà giao, giữ riêng tư và tài sản|Chốt nhu cầu từng nhà và vật tư bề mặt~Dùng một danh sách cho mọi nhà|Chia đội theo kỹ năng và giờ gia đình có mặt~Xếp đội trùng giờ ở hai nhà|Dừng khi thấy đồ hỏng sẵn, ghi nhận với chủ~Tự sửa đồ chưa được giao|Đối danh sách việc và tài sản cùng chủ nhà~Chỉ gửi ảnh phòng sạch|Phiếu yêu cầu từng nhà;Lịch đội và giờ có mặt;Biên bản hiện trạng;Xác nhận việc và tài sản
ice_cream|làm mẻ lạnh;bán kem|Mẻ kem theo vị|mẻ|Sữa, đường và nguyên liệu vị cân cho hai mươi phần kem|Đúng công thức, mẻ đủ lạnh và ghi lịch bảo quản|Chọn mẻ theo vị và thời gian cấp đông~Làm mọi vị chung một mẻ|Xếp trạm làm và tủ lạnh theo thời gian mẻ~Cho mẻ chưa đông chiếm quầy bán|Cách ly mẻ mất lạnh, thay mẻ đạt~Làm đông lại mẻ đã mất lạnh để bán|So nhiệt bảo quản và mẫu vị từng mẻ~Chỉ đếm số phần đã bán|Phiếu công thức và giờ đông;Lịch trạm và tủ;Phiếu cách ly mất lạnh;Nhật ký nhiệt và mẫu vị
nail|thợ mẫu;khử khuẩn|Bộ móng theo mẫu|khách|Sơn, vật tư cá nhân, dụng cụ đã xử lý và thời gian thợ một khách|Mẫu được xác nhận, vật tư phù hợp và dụng cụ sạch từng lượt|Chốt mẫu, vật tư và thời lượng từng khách~Nhận mẫu phức tạp với giờ làm mẫu đơn|Xếp thợ mẫu và bàn sạch theo lịch~Dùng bàn chưa xử lý cho khách kế|Dừng dụng cụ chưa đạt, thay bộ sạch~Lau nhanh dụng cụ rồi làm tiếp|So mẫu, độ hoàn thiện và nhật ký xử lý dụng cụ~Chỉ kiểm màu sơn từ xa|Phiếu mẫu và thời lượng;Lịch thợ và bàn;Phiếu thay bộ dụng cụ;Xác nhận mẫu và vệ sinh
pagoda|hướng dẫn khách;điều phối công quả|Buổi công quả|buổi|Dụng cụ vệ sinh, nước uống và danh sách việc tình nguyện một buổi|Tôn trọng riêng tư thẻ chúc, tự nguyện và không quy tiền thành công đức|Chốt việc công quả theo nhu cầu và người tự nguyện~Xếp việc theo số tiền đóng góp|Chia nhóm hướng dẫn khách và nhóm vệ sinh~Giao người vắng mặt vẫn tính đủ nhóm|Ẩn thẻ chúc riêng tư bị đặt nhầm, báo người gửi~Đọc thẻ riêng tư cho mọi người nghe|Đối việc đã làm và xác nhận người phụ trách~Nghiệm thu bằng tổng tiền cúng|Danh sách việc tự nguyện;Lịch nhóm công quả;Phiếu giữ riêng tư;Xác nhận hoàn tất công quả
pho|nấu nước dùng;ra tô|Mẻ phở theo đoàn|mẻ|Xương, thịt, bánh phở và rau định lượng cho hai mươi tô|Nước dùng đúng mẻ, giữ nóng và tách yêu cầu từng khách|Lập mẻ nước dùng theo thời gian nấu và giờ nhận~Nấu gấp không đủ thời gian mẻ|Chia bếp nấu và trạm ra tô theo nhịp khách~Một trạm vừa xử lý thịt sống vừa ra tô|Tách mẻ không đạt, nấu bổ sung và báo trễ~Pha mẻ không đạt với mẻ tốt|Kiểm mẫu nước dùng, nhiệt và số tô theo phiếu~Chỉ kiểm số tô đã bán|Lịch nấu và định lượng;Lịch bếp và trạm tô;Phiếu tách mẻ;Mẫu nước dùng và giao tô
com|bếp suất ăn;đóng hộp|Lô suất cơm|lô|Gạo, món mặn, rau và hộp cho hai mươi suất theo hợp đồng|Đúng khẩu phần, giữ nóng và giao đủ trong khung giờ|Chốt khẩu phần và lịch giao theo khách tổ chức~Lấy khẩu phần chung cho mọi hợp đồng|Chia bếp món và bàn đóng hộp theo đợt~Đóng toàn bộ trước giờ giao quá sớm|Tách hộp thiếu món, bổ sung và ghi kiểm lại~Giao thiếu để xe kịp giờ|Cân kiểm phần mẫu và ký nhận đủ suất~Chỉ đếm thùng trên xe|Phiếu khẩu phần và lịch giao;Lịch bếp và đóng hộp;Phiếu bổ sung món;Biên nhận suất và kiểm mẫu
photobooth|chụp ảnh;chỉnh ảnh|Buổi chụp bàn giao|buổi|Lịch máy, phông, ảnh chọn, chỉnh màu và bản in theo thỏa thuận|Đúng quyền dùng ảnh, đủ bản chọn và màu in được duyệt|Chốt số ảnh, phông và quyền sử dụng~Hứa mọi ảnh đẹp trước khi chốt yêu cầu|Khóa lịch buồng chụp và bàn chỉnh riêng~Cho hai buổi dùng một máy cùng giờ|Chụp bù ảnh lỗi nét và xin duyệt ảnh thay~Tăng nét tự động rồi giao ảnh lỗi|Đối bản chọn, màu in và quyền chia sẻ~Đăng ảnh khách làm mẫu khi chưa có đồng ý|Phiếu ảnh và quyền dùng;Lịch máy và chỉnh ảnh;Phiếu chụp bù;Biên nhận bản chọn và màu
giupviec|vệ sinh bề mặt;kiểm bàn giao|Ca vệ sinh theo giờ|nhà một ca|Dụng cụ, hóa chất đúng bề mặt và danh sách khu vực cần vệ sinh|Không làm hỏng bề mặt, ghi tài sản trước sau và đúng giờ|Khảo sát bề mặt, chốt khu vực và giờ làm~Chọn hóa chất mạnh cho mọi bề mặt|Chia đội khu ướt và khu khô với dụng cụ riêng~Dùng chung khăn cho mọi khu|Dừng khi bề mặt đổi màu, báo chủ và ghi hiện trạng~Che vết đổi màu bằng đồ đạc|Kiểm từng khu và tài sản với người nhận~Chỉ nghiệm thu theo giờ đã làm|Phiếu bề mặt và phạm vi;Lịch đội và dụng cụ;Biên bản bề mặt;Xác nhận từng khu và tài sản
naucom|lên thực đơn;bếp gia đình|Bữa cơm gia đình|bữa|Nguyên liệu theo thực đơn, số người và dụng cụ tách dị ứng một nhà|Đúng món đã duyệt, dị ứng và giờ dùng bữa|Chốt món, dị ứng và số người từng nhà~Dùng thực đơn mẫu không hỏi dị ứng|Chia đội bếp theo địa chỉ và giờ ăn~Xếp một đầu bếp ở hai nhà cùng giờ|Thay nguyên liệu chỉ sau khi gia đình đồng ý~Đổi nguyên liệu tùy ý khi thiếu|Đối thực đơn, khẩu phần và xác nhận gia đình~Chỉ gửi ảnh mâm cơm|Phiếu thực đơn và dị ứng;Lịch đội bếp;Phiếu duyệt thay nguyên liệu;Biên nhận bữa ăn gia đình
babysitter|chăm trẻ;giám sát ca|Ca chăm trẻ có bàn giao|trẻ một ca|Lịch ăn nghỉ, vật dụng riêng, người chăm và phiếu đón một trẻ|Người chăm đủ điều kiện, đúng người đón và không bỏ trống giám sát|Chốt lịch trẻ, liên hệ và người được đón~Dùng lịch chung bỏ thông tin người đón|Bố trí chăm và giám sát, bàn giao trước đổi ca~Cho người chăm rời trước khi ca sau đến|Giữ trẻ cùng người giám sát khi người lạ đến đón~Giao trẻ cho người tự nhận là quen|Đối nhật ký ăn nghỉ và người đón đã xác nhận~Chỉ báo gia đình trẻ đã về|Phiếu lịch và người đón;Lịch chăm và giám sát;Biên bản xác minh người đón;Nhật ký và bàn giao trẻ
library|biên mục;bảo quản|Lô tư liệu luân chuyển|lô|Mười tài liệu có mã, tình trạng, nơi lưu và phiếu chuyển liên điểm|Đúng mã, điều kiện bảo quản và quyền tiếp cận tài liệu|Lập danh mục chuyển theo nhu cầu và độ quý hiếm~Chuyển sách theo số lượng đều mỗi điểm|Chia nhóm biên mục và bảo quản theo loại tài liệu~Xếp tài liệu cần bảo quản vào kệ thường|Cách ly tài liệu ẩm, ghi tình trạng và chuyển xử lý~Để chung kệ chờ đợt kiểm sau|Đối mã, tình trạng và chữ ký nơi nhận~Chỉ đếm thùng sách|Danh mục và quyền tiếp cận;Lịch biên mục và bảo quản;Phiếu tình trạng ẩm;Phiếu nhận theo mã tư liệu
pilot|lập kế hoạch;kiểm điều kiện tổ bay|Hồ sơ điều phối chuyến|chuyến|Kế hoạch bay, thời tiết, lịch nghỉ và hồ sơ điều kiện tổ bay|Theo quy trình hiện hành, đủ điều kiện và không tự tăng quyền khai thác|Rà thời tiết và điều kiện trước chốt kế hoạch~Giữ giờ bay bất kể thay đổi thời tiết|Chọn tổ đủ điều kiện, kiểm thời gian nghỉ~Giao tổ chưa đủ nghỉ để giữ lịch|Chuyển phụ trách xem xét khi điều kiện thay đổi~Tự bỏ bước kiểm để tránh trễ|Kiểm hồ sơ, xác nhận người có thẩm quyền~Nghiệm thu theo số chuyến dự kiến|Hồ sơ kế hoạch và thời tiết;Lịch nghỉ và điều kiện tổ;Phiếu chuyển xem xét;Xác nhận hồ sơ khai thác
flight_attendant|phục vụ khoang;kiểm an toàn|Kế hoạch phục vụ chuyến|chuyến|Danh sách nhu cầu khách, suất ăn và phân vùng phục vụ của tổ|Đúng yêu cầu đặc biệt, đủ người và kiểm an toàn theo quy trình|Đối nhu cầu đặc biệt và suất ăn trước phân khoang~Chia suất ăn đều bỏ yêu cầu riêng|Chia tổ theo khoang, giữ người kiểm an toàn~Dồn cả tổ phục vụ bỏ lượt kiểm|Cách ly suất sai yêu cầu, xin thay và báo phụ trách~Giao suất gần giống cho khách|Đối suất đặc biệt và biên bản kiểm khoang~Chỉ đếm khay đã phát|Phiếu nhu cầu và suất ăn;Lịch tổ theo khoang;Phiếu thay suất;Biên bản kiểm và bàn giao khoang
oil|kiểm giấy phép;bảo dưỡng|Gói bảo dưỡng có kiểm soát|thiết bị|Hồ sơ công việc, vật tư đúng mã, lịch cô lập và kiểm sau bảo dưỡng|Đúng giấy phép, đủ điều kiện và người phụ trách xác nhận|Rà giấy phép, lịch cô lập và mã vật tư~Chọn giờ làm khi máy vẫn đang vận hành|Bố trí tổ đủ điều kiện và người kiểm cô lập~Giao người bảo dưỡng tự bỏ bước kiểm|Dừng việc khi giấy phép chưa khớp, báo phụ trách~Làm trước rồi bổ sung giấy phép|Kiểm biên bản công việc và xác nhận hoàn trả thiết bị~Chỉ đếm số vật tư đã thay|Giấy phép và lịch cô lập;Lịch tổ và người kiểm;Phiếu dừng công việc;Biên bản kiểm và hoàn trả
hr_admin|tuyển dụng;quản lý hồ sơ|Đợt hồ sơ nhân sự|đợt|Lịch phỏng vấn, hồ sơ có quyền xem và danh sách việc tiếp nhận|Bảo mật ứng viên, đúng người duyệt và không trùng lịch|Chốt vị trí, tiêu chí và lịch phỏng vấn~Đặt lịch trước khi chốt tiêu chí|Chia người phỏng vấn và người quản hồ sơ theo quyền~Cho cả nhóm xem mọi hồ sơ cá nhân|Thu hồi quyền gửi nhầm, báo người phụ trách dữ liệu~Chuyển tiếp hồ sơ nhầm cho cả nhóm|Đối lịch, phê duyệt và bàn giao hồ sơ đúng quyền~Chỉ đếm hồ sơ đã nhận|Kế hoạch vị trí và lịch;Danh sách phân quyền;Phiếu xử lý gửi nhầm;Biên bản tiếp nhận nhân sự
secretary|điều phối lịch;theo dõi đầu việc|Gói điều phối cuộc họp|cuộc họp|Lịch, phòng, tài liệu đúng quyền và biên bản giao đầu việc|Không trùng người phòng, tài liệu đúng người và có hạn thực hiện|Chốt mục tiêu, thành phần và quyền xem trước gửi lịch~Mời toàn bộ danh bạ cho tiện|Giữ phòng và người ghi biên bản theo giờ~Đặt hai cuộc họp cùng một phòng|Đổi lịch xung đột và xác nhận lại người tham gia~Đổi lịch mà không báo thành phần|Đối biên bản, người nhận việc và hạn hoàn tất~Chỉ xác nhận cuộc họp đã diễn ra|Phiếu mục tiêu và thành phần;Lịch phòng và thư ký;Xác nhận đổi lịch;Biên bản đầu việc có hạn
it_helpdesk|phân loại ticket;khôi phục hệ thống|Gói xử lý sự cố IT|ticket|Mã yêu cầu, mức ảnh hưởng, quyền truy cập và biên bản kiểm phục hồi|Được phép truy cập, có phương án khôi phục và người dùng xác nhận|Ưu tiên theo ảnh hưởng và phương án khôi phục~Xử lý theo người gọi to nhất|Chia ticket theo kỹ năng và quyền hệ thống~Dùng chung tài khoản quản trị cho cả nhóm|Dừng thay đổi lỗi, khôi phục theo phương án đã duyệt~Thử thêm thay đổi khi chưa ghi vết|Kiểm dịch vụ với người dùng và đóng quyền tạm~Đóng ticket ngay khi máy khởi động|Bảng ảnh hưởng và phương án;Lịch kỹ năng và quyền;Nhật ký thay đổi và khôi phục;Xác nhận người dùng và đóng quyền
railway|trực điểm;kiểm thiết bị|Ca kiểm tra tuyến|ca|Lịch trực, danh mục thiết bị và hồ sơ bàn giao theo quy trình|Không bỏ điểm trực, không tăng tải hoặc thay quy trình an toàn|Chốt danh mục kiểm và lịch trực theo quy trình~Giảm lượt kiểm để tăng thông tuyến|Bố trí người đủ điều kiện và bàn giao trước đổi ca~Cho ca cũ về trước khi người mới tới|Báo thiết bị bất thường, giữ quy trình và chờ phụ trách~Tự bỏ bước vận hành để tránh chậm|Đối nhật ký điểm trực và biên bản bàn giao~Chỉ đếm lượt tàu qua|Kế hoạch kiểm và lịch trực;Phiếu người đủ điều kiện;Nhật ký báo bất thường;Biên bản bàn giao điểm
nurse|chăm sóc;kiểm giao ca|Ca chăm sóc có giám sát|ca|Kế hoạch chăm, vật tư, hồ sơ y lệnh và bàn giao người bệnh|Theo y lệnh và phạm vi chuyên môn, bất thường báo người phụ trách|Rà kế hoạch chăm và hồ sơ y lệnh của ca~Dùng kế hoạch ca trước không đối chiếu|Chia người chăm theo mức cần hỗ trợ và lịch giao ca~Chia đều số giường không xét nhu cầu|Báo bác sĩ khi thông tin chưa khớp, giữ hồ sơ kiểm lại~Tự sửa y lệnh cho khớp vật tư|Đối hồ sơ chăm và xác nhận bàn giao người bệnh~Chỉ đếm vật tư đã dùng|Kế hoạch chăm và y lệnh;Lịch chăm và bàn giao;Phiếu báo người phụ trách;Biên bản giao ca chăm sóc
lighthouse|trực đèn;bảo dưỡng|Ca tín hiệu hải đăng|ca|Lịch trực, vật tư đúng mã, kiểm tín hiệu chính và dự phòng|Giữ tín hiệu theo quy trình, kiểm dự phòng và ghi bàn giao|Chốt lịch bảo dưỡng theo yêu cầu duy trì tín hiệu~Tắt toàn bộ tín hiệu để bảo dưỡng nhanh|Phân tổ trực và tổ kiểm dự phòng không trùng ca~Cho tổ trực rời điểm khi tổ sau chưa tới|Báo lỗi và dùng phương án dự phòng đã duyệt~Chờ hết ca mới báo lỗi tín hiệu|Đối nhật ký đèn, dự phòng và bàn giao ca~Chỉ kiểm đèn sáng tại lúc ký|Lịch duy trì tín hiệu;Lịch trực và kiểm dự phòng;Phiếu báo lỗi tín hiệu;Nhật ký đèn và bàn giao
rescue|tiếp nhận cuộc gọi;điều phối đội|Ca tổng đài cứu hộ|ca|Phiếu cuộc gọi, vị trí đã xác minh, mức ưu tiên và bàn giao đội|Theo quy trình, đúng vị trí và giữ thông tin người gọi riêng tư|Phân loại cuộc gọi và xác minh vị trí theo quy trình~Chỉ ghi địa chỉ lần đầu nghe được|Chia tiếp nhận với điều phối theo đội sẵn sàng~Giao một đội đang bận thêm hai vụ|Cập nhật vị trí sai và báo ngay đội được giao~Đợi hết cuộc gọi mới sửa vị trí|Đối phiếu chuyển, đội nhận và kết quả hậu kiểm~Đóng cuộc gọi ngay sau chuyển máy|Phiếu vị trí và ưu tiên;Bảng đội sẵn sàng;Nhật ký cập nhật vị trí;Xác nhận đội nhận và hậu kiểm
lifeguard|quan sát vùng;giám sát ca|Ca an toàn hồ|ca|Sơ đồ vùng quan sát, lịch người trực và kiểm dụng cụ theo quy trình|Không có vùng mù hoặc khoảng trống trực, đủ điều kiện chuyên môn|Chốt vùng quan sát và lịch kiểm trước mở ca~Giữ sơ đồ cũ dù khu hồ thay đổi|Bố trí người trực từng vùng và đổi ca có bàn giao~Gộp hai vùng khuất cho một người|Báo thiếu người, hạn chế vùng theo quy trình phụ trách~Để vùng trống vẫn nhận khách|Đối nhật ký vùng và biên bản diễn tập kiểm dụng cụ~Chỉ đếm số khách hết ca|Sơ đồ vùng và lịch kiểm;Lịch trực từng vùng;Phiếu báo thiếu người;Nhật ký vùng và kiểm dụng cụ
police|tiếp nhận hồ sơ;kiểm chứng cứ|Chuyên đề hồ sơ địa bàn|bộ hồ sơ|Phiếu tiếp nhận, tài liệu có nguồn, phân công và kiểm tra nghiệp vụ|Theo thẩm quyền hiện hành, bảo mật và không đổi tiền lấy chức vụ|Chốt phạm vi hồ sơ và hạn xử lý theo thẩm quyền~Nhận cả việc ngoài thẩm quyền để đủ chỉ tiêu|Chia tiếp nhận với kiểm nguồn chứng cứ~Để người lập tự xác nhận mọi chứng cứ|Treo tài liệu chưa rõ nguồn, yêu cầu xác minh~Kết luận ngay từ một lời kể|Kiểm căn cứ, dấu vết xử lý và người duyệt đúng quyền~Đánh giá theo số hồ sơ đóng nhanh|Danh mục hồ sơ và thẩm quyền;Phân công kiểm chứng cứ;Phiếu xác minh nguồn;Biên bản duyệt nghiệp vụ
zpop|tư vấn phiên bản;đối soát đặt trước|Bộ album theo phiên bản|bộ|Album, phụ kiện công bố và phiếu phiên bản; tiền cọc theo dõi riêng|Đúng phiên bản, nguyên niêm và không lẫn cọc với doanh thu|Chốt phiên bản và số đặt trước theo cọc riêng~Đặt số lượng theo lượt hỏi chưa xác nhận|Chia quầy nhận album và người đối soát cọc~Cho quầy giao bỏ qua sổ đặt trước|Tách kiện thiếu phụ kiện, xác nhận đổi với khách~Giao phiên bản khác khi bản đặt đã hết|Đối phiên bản, phụ kiện và phần cọc đã cấn~Cộng cả cọc lẫn tiền thu vào doanh thu|Bảng phiên bản và sổ cọc;Lịch nhận và đối soát;Phiếu thiếu phụ kiện;Biên nhận album và cấn cọc
art_studio|họa sĩ;phụ trách trưng bày|Hợp đồng tranh đặt|tác phẩm|Phác thảo được duyệt, vật liệu, khung và công hoàn thiện một tác phẩm|Đúng kích thước, chất liệu, quyền sử dụng và mốc khách duyệt|Chốt phác thảo, vật liệu và quyền dùng tác phẩm~Vẽ ngay khi chưa duyệt phác thảo|Xếp bàn vẽ và khu khô theo vật liệu, phân họa sĩ~Đặt tranh chưa khô vào khu đóng gói|Xin duyệt thay vật liệu trước thực hiện~Thay chất liệu để giảm giá vốn không báo|So tác phẩm với phác thảo và phiếu bàn giao~Chỉ nghiệm thu qua ảnh thu nhỏ|Phác thảo và quyền sử dụng;Lịch bàn vẽ và khu khô;Phiếu duyệt vật liệu;Biên nhận tác phẩm và khung
lawyer|luật sư phụ trách;soát hồ sơ|Gói hồ sơ tư vấn|hồ sơ|Phạm vi tư vấn, tài liệu khách, lịch hạn và bản bàn giao được soát|Kiểm xung đột lợi ích, bảo mật và không bảo đảm thắng kiện|Kiểm xung đột lợi ích và phạm vi trước nhận~Nhận hồ sơ trước rồi kiểm xung đột sau|Giao luật sư đủ điều kiện và người soát theo hạn~Giao người chưa đủ điều kiện tự ký tư vấn|Dừng phần thiếu tài liệu, xin bổ sung và báo hạn~Tự suy đoán sự kiện để nộp đúng giờ|Đối phạm vi, căn cứ và xác nhận bàn giao khách~Nghiệm thu bằng lời hứa chắc thắng|Phiếu xung đột và phạm vi;Lịch luật sư và người soát;Danh sách tài liệu còn thiếu;Biên bản bàn giao tư vấn
laundry|phân loại đồ;vận hành máy|Mẻ giặt có giao nhận|mẻ|Đồ gắn mã, chất giặt đúng loại, chu kỳ máy và gói trả từng khách|Tách màu chất liệu, đúng nhãn đồ và truy được món thất lạc|Chốt loại vải và chu kỳ trước đặt lịch máy~Gộp mọi chất liệu vào chu kỳ nhanh|Khóa máy theo chu kỳ, tách bàn phân loại và gấp~Xếp hai mẻ chồng giờ trên cùng máy|Treo gói thiếu món, truy mã và báo khách~Bù món tương tự của khách khác|Đối mã món, độ sạch khô và phiếu trả~Chỉ cân tổng đồ trả|Phiếu đồ và chu kỳ;Lịch máy không chồng;Phiếu truy món thiếu;Biên nhận từng mã đồ
restore|khám đồ;phục hồi|Lô đồ phục chế có biên bản|món|Phiếu khám dấu hiệu, yêu cầu khách đã chốt, linh kiện ghi nguồn và ảnh trước sau từng món|Giữ hồn món đồ, ghi đúng tuổi, không làm giả và không tháo đồ khách khác|Chốt dấu hiệu hư hỏng và yêu cầu khách trước khi nhận~Nhận đồ rồi mới hỏi khách muốn gì|Chia bàn khám đồ với bàn phục hồi theo chất liệu~Để một thợ làm mọi chất liệu cùng giờ|Thiếu linh kiện thì chế lại cùng vật liệu và ghi phiếu~Tháo linh kiện từ đồ của khách khác|Đối ảnh trước sau, tuổi đồ và hạng mục từng món~Chỉ đếm số món đã trả|Phiếu khám và yêu cầu khách;Lịch bàn khám và bàn phục hồi;Sổ linh kiện chế lại;Biên bản phục chế có ảnh
post_office|phân kiện;đối soát bưu chính|Tuyến bưu gửi|tuyến|Mười bưu gửi có mã, lịch tuyến, xác nhận phát và sổ COD riêng|Đúng người nhận, giữ hạn chuyển và tách tiền giữ hộ|Chốt tuyến theo hạn phát, loại kiện và COD~Chia đều kiện bỏ qua hạn phát|Giao tổ phân kiện và tổ tuyến theo tải lịch~Gán cùng tổ cho hai tuyến trùng giờ|Ghi lý do hoàn, giữ nguyên mã và sổ COD~Ghi phát thành công cho kiện bị hoàn|Đối mã phát hoàn và tiền COD giữ hộ~Cộng tiền COD thành thu nhập cá nhân|Bảng tuyến và hạn phát;Lịch tổ phân kiện và tuyến;Phiếu hoàn theo mã;Đối soát phát hoàn và COD
customs|kiểm tra hồ sơ;kiểm hóa thực tế|Chuyên đề kiểm soát cửa khẩu|lô hàng|Tờ khai điện tử, kết quả phân luồng, biên bản kiểm hóa và sổ hàng tạm giữ|Đúng luồng, đủ chứng từ, không nhận gì của doanh nghiệp|Chốt danh mục lô theo luồng và hạn thông quan~Gom mọi lô vào luồng xanh cho nhanh|Chia tổ kiểm hồ sơ với tổ kiểm thực tế~Để một người vừa khai vừa kiểm|Niêm phong hàng tạm giữ, ghi biên lai từng món~Để hàng tạm giữ ngoài kho không sổ|Đối chiếu tờ khai, biên bản và số thuế đã thu~Đánh giá theo số lô thông quan nhanh|Danh mục lô theo luồng;Phân công kiểm hồ sơ và thực tế;Sổ hàng tạm giữ có biên lai;Đối soát tờ khai và thuế
banquet|bếp tiệc;sảnh sự kiện|Ca nhà hàng tiệc|ca|Phiếu tiệc, định lượng sơ chế, phiếu kiểm nhận hàng, sơ đồ sảnh và sổ vệ sinh đầu, cuối ca|Bếp sạch, món đúng lưu ý từng bàn, sảnh đúng yêu cầu khách và tắt điện an toàn|Chốt số bàn, phòng tiệc và thực đơn theo phiếu đặt~Nhận tiệc trước rồi mới tính số bàn|Chia phụ bếp, đầu bếp và người chạy sảnh theo giờ ra món~Để một người vừa nấu vừa bày sảnh|Dừng món sai nhiệt, đổi món theo thẻ dị ứng và báo bàn~Ra món nguội cho kịp giờ|Đối chiếu sổ vệ sinh đầu ca, phiếu ra món và biên bản tắt điện~Chỉ đếm số bàn đã phục vụ|Phiếu tiệc và sơ đồ sảnh;Lịch phụ bếp, đầu bếp và sảnh;Phiếu kiểm quầy ra món;Sổ vệ sinh và tắt điện cuối ca
reception|lễ tân;điều phối phòng|Ca quầy lễ tân|ca|Bảng phòng, bảng móc chìa, sổ giao ca, lịch dọn phòng và lịch dịch vụ của một ca|Đúng phòng đúng người, đủ yêu cầu khách, chìa đúng số và sổ giao ca không sót việc|Chốt bảng phòng theo lời khách và tình trạng buồng~Giao phòng đầu tiên còn trống cho nhanh|Chia quầy, buồng phòng và xe hành lý theo giờ khách tới~Để một người vừa trực quầy vừa khiêng hành lý cả đoàn|Xếp lại phòng sai yêu cầu, đổi chìa nhầm và ghi lý do vào sổ~Đổi phòng cho khách mà không ghi sổ|Đối chiếu bảng phòng, chìa đã giao và sổ giao ca từng ca~Chỉ đếm số khách đã nhận phòng|Bảng phòng và lời yêu cầu;Lịch quầy và buồng phòng;Sổ đổi phòng và đổi chìa;Sổ giao ca và việc còn dở
teller|giao dịch viên;kiểm soát quỹ|Ca quầy giao dịch|ca|Phiếu giao dịch, khay tiền, sổ quỹ đầu ca, nhật ký ATM và biên nhận bàn giao của một ca|Đúng người, đúng tiền, quỹ khớp từng đồng và không lộ thông tin khách|Chốt số quầy mở theo lượng khách và ngày lương hưu~Mở một quầy rồi để hàng chờ tự tan|Tách người lập và người kiểm soát, hai người cho mỗi lần mở ATM~Để một người vừa chi vừa tự duyệt|Dừng giao dịch lệch số, hỏi lại khách và lập biên bản~Làm theo phiếu cho kịp rồi sửa sau|Đối chiếu biên nhận với sổ giao dịch, quỹ đầu ca và tiền quầy cuối ca~Chỉ đếm số khách đã gọi|Lịch quầy và ngày cao điểm;Phân công lập và kiểm soát;Biên bản giao dịch treo;Sổ bàn giao quỹ cuối ca
hotel|lễ tân;buồng phòng|Ca vận hành khách sạn|ca|Bảng phòng, phiếu đặt, lịch buồng phòng, sổ giặt là và lịch bảo trì của một ca|Phòng sạch đúng yêu cầu, không giao trùng phòng, đồ khách thất lạc có sổ|Chốt bảng phòng theo phiếu đặt và tình trạng buồng~Giao phòng chưa dọn cho khách tới sớm|Chia lễ tân, buồng phòng, giặt là và bảo trì theo giờ cao điểm~Để một người vừa trực quầy vừa dọn cả tầng|Khóa phòng hỏng, đổi phòng cho khách và hẹn nhà thầu~Bán phòng hỏng rồi xin lỗi sau|Đối chiếu phòng sạch, đồ thất lạc và phiếu giặt từng ca~Chỉ đếm số phòng đã bán|Bảng phòng và phiếu đặt;Lịch ca theo vị trí;Sổ phòng khóa và hẹn thợ;Sổ đồ thất lạc và phiếu giặt
research|nghiên cứu viên;kỹ thuật viên phòng thí nghiệm|Đề tài nghiên cứu ứng dụng|đề tài|Đề cương được duyệt, mẫu có mã, khay đối chứng, sổ thí nghiệm đánh số trang và biên bản hội đồng|Số liệu thật, có đối chứng, ghi đủ lần hỏng và kết luận đúng mức dữ liệu|Chốt câu hỏi, đối chứng và số lần lặp trước khi làm~Làm trước rồi mới nghĩ đối chứng|Chia người lấy mẫu, người đo và người ghi sổ theo lịch~Để một người vừa làm vừa tự chấm kết quả|Ghi mẫu hỏng, lấy mẫu dự phòng cùng lô và báo hội đồng~Đổ mẫu khác vào cho đủ cân|Đối chiếu sổ gốc, biên bản hội đồng và số liệu thô~Chỉ nộp biểu đồ đẹp|Đề cương và lịch lặp;Phân công lấy mẫu và ghi sổ;Sổ mẫu hỏng và mẫu dự phòng;Biên bản hội đồng và số liệu thô
radio|đọc bản tin;dựng chương trình|Ca phát sóng|ca|Lịch phát sóng, bản tin đã kiểm chứng, kịch bản quảng cáo đã duyệt, danh sách bài có bản quyền và sổ sự cố|Đúng tin, đúng tên, chỉ phát bản đã duyệt và không để sóng câm|Chốt bản tin theo thứ tự tin khẩn và giờ phát~Đọc tin theo thứ tự gửi tới đài|Chia người đọc tin, DJ và kỹ thuật theo khung giờ~Để một người vừa đọc tin vừa trực máy phát|Rút spot chưa duyệt, đọc đính chính và báo nhà tài trợ~Phát bản mới nhất cho kịp giờ|Đối chiếu sổ duyệt kịch bản, sổ cuộc gọi và sổ sự cố~Chỉ đếm số giờ đã phát|Lịch phát sóng và bản tin;Phân ca đọc tin, DJ và kỹ thuật;Sổ duyệt kịch bản;Sổ sự cố và sổ cuộc gọi'''

# Procurement uses divisible real base units, not a monetary leftover without
# stock. Each listed material has a fixed 1 xu/base-unit experimental price;
# bundle size never changes its unit price. Bundle specifications above describe
# the work delivered, while these names identify the purchased consumable.
_SUPPLIES = '''mother_baby|Khăn chăm bé|chiếc|100
pharmacy|Gạc đóng lẻ|miếng|100
accounting|Giấy chứng từ|tờ|500
customer_care|Giấy phiếu hỗ trợ|tờ|100
teacher|Giấy học liệu|tờ|500
tour_guide|Nước uống đoàn|ml|1000
milk_tea|Nguyên liệu trà sữa định lượng|g|1000
restaurant|Nguyên liệu mì định lượng|g|1000
cafe_bakery|Nguyên liệu bánh định lượng|g|1000
florist|Dây buộc hoa|cm|1000
grocery|Gạo đóng giỏ|g|1000
repair|Dung dịch vệ sinh linh kiện|ml|500
farm|Hạt giống|g|1000
delivery|Nhiên liệu tuyến giao|ml|1000
homestay|Dung dịch vệ sinh phòng|ml|1000
pet_care|Thức ăn thú theo khẩu phần|g|1000
salon|Sản phẩm chăm tóc|ml|500
corp_accounting|Giấy đối chiếu số dư|tờ|500
tax_payroll|Giấy hồ sơ lương|tờ|500
group_accounting|Giấy bảng hợp nhất|tờ|500
clothing|Vải may trang phục theo mẫu|cm|1000
pet_shop|Thức ăn thú đóng lô|g|1000
tra_da|Trà khô|g|500
fruit|Trái cây đóng giỏ|g|1000
garbage|Túi phân loại rác|chiếc|100
drain|Dung dịch vệ sinh thiết bị|ml|1000
homemaker|Dung dịch chăm bề mặt|ml|1000
ice_cream|Nguyên liệu kem định lượng|g|1000
nail|Sơn và dung dịch làm móng|ml|100
pagoda|Nước uống công quả|ml|1000
pho|Nguyên liệu phở định lượng|g|1000
com|Nguyên liệu suất ăn định lượng|g|1000
photobooth|Mực in ảnh|ml|100
giupviec|Dung dịch vệ sinh bề mặt|ml|1000
naucom|Nguyên liệu bữa gia đình|g|1000
babysitter|Khăn dùng riêng cho trẻ|chiếc|100
library|Giấy bảo quản tư liệu|tờ|100
pilot|Giấy hồ sơ điều phối|tờ|100
flight_attendant|Khăn phục vụ khoang|chiếc|100
oil|Dung dịch bảo dưỡng|ml|1000
hr_admin|Giấy hồ sơ nhân sự|tờ|100
secretary|Giấy tài liệu cuộc họp|tờ|100
it_helpdesk|Dung dịch vệ sinh thiết bị IT|ml|500
railway|Dung dịch vệ sinh thiết bị trực|ml|500
nurse|Gạc chăm sóc đóng lẻ|miếng|100
lighthouse|Dung dịch bảo dưỡng đèn|ml|500
rescue|Giấy phiếu điều phối|tờ|100
lifeguard|Dung dịch vệ sinh dụng cụ hồ|ml|500
police|Giấy hồ sơ nghiệp vụ|tờ|100
zpop|Giấy bảo vệ album|tờ|100
art_studio|Màu vẽ|ml|100
lawyer|Giấy hồ sơ tư vấn|tờ|500
laundry|Nước giặt|ml|1000
restore|Sáp ong phục chế|g|500
post_office|Giấy gói bưu gửi|tờ|100
customs|Tem niêm phong hải quan|cái|100
hotel|Bộ tiện nghi phòng|bộ|100
banquet|Bao tay dùng một lần|đôi|100
reception|Thẻ gửi hành lý hai nửa|thẻ|100
teller|Dây thun buộc cọc tiền|sợi|100
research|Ống nghiệm dùng một lần|ống|100
radio|Băng dự phòng phát sóng|cuộn|100'''

# Approved scope names; static runtime data, no documentation import.
_SCOPES = '''mother_baby|retail|Tiệm chuyên đồ sơ sinh;Cửa hàng mẹ bé;Trung tâm mẹ bé;Hai cửa hàng;Cụm ba tiệm;Chuỗi năm tiệm;Chuỗi khu vực;Mạng lưới mẹ bé|Tư vấn theo tuổi, truy lô, đổi trả liên điểm|quầy tư vấn
pharmacy|retail|Quầy mở rộng;Nhà thuốc chuẩn;Điểm cung ứng vật tư;Hai nhà thuốc;Cụm ba điểm;Chuỗi năm điểm;Chuỗi khu vực;Mạng lưới cung ứng|Kiểm phiếu, truy xuất lô, thu hồi liên điểm; giữ giới hạn chuyên môn|quầy có người phụ trách
accounting|professional|Bàn dịch vụ;Văn phòng nhỏ;Văn phòng nhiều nhóm;Hai nhóm khách;Cụm văn phòng;Chuỗi dịch vụ;Trung tâm soát xét;Mạng lưới kế toán|Phân công bộ sổ, kiểm chéo, nghiệm thu từng khách|nhóm hồ sơ
customer_care|agency|Kèm nhân viên;Điều phối ca;Quản lý nhóm dự án;Phối hợp hai nhóm;Điều phối cụm;Dự án liên phòng;Vận hành khu vực;Chương trình toàn hệ thống|Chia yêu cầu theo độ khó, kiểm lời hẹn, xử lý sự cố|nhóm hỗ trợ
teacher|agency|Kèm giáo viên mới;Dẫn chuyên đề;Điều phối tổ dự án;Dự án liên lớp;Dự án liên tổ;Dự án liên trường;Điều phối khu vực;Chương trình chuyên môn|Phân lịch, duyệt bài, hỗ trợ lớp; không mua chức hiệu trưởng|nhóm chuyên môn
tour_guide|service|Nhóm hướng dẫn;Văn phòng tour;Điều hành nhiều đoàn;Hai điểm khởi hành;Cụm điểm tour;Chuỗi văn phòng;Điều hành khu vực;Mạng lưới du lịch|Chia đoàn, đặt dịch vụ, xử lý trễ và kiểm người|đoàn có hướng dẫn viên
milk_tea|food|Quầy lớn;Cửa hàng trà sữa;Cửa hàng có bếp sơ chế;Hai cửa hàng;Cụm ba quán;Chuỗi năm quán;Chuỗi khu vực;Thương hiệu trà sữa|Công thức mới, mẻ ủ, giao nguyên liệu, kiểm vị|trạm pha chế
restaurant|food|Quán mở rộng;Nhà hàng mì;Bếp phục vụ đoàn;Hai nhà hàng;Cụm ba quán;Chuỗi năm quán;Chuỗi khu vực;Hệ thống nhà hàng|Chia bếp, menu theo điểm, vệ sinh và nghiệm thu tiệc|trạm bếp
cafe_bakery|food|Quán bánh lớn;Café có xưởng bánh;Bếp bánh trung tâm;Hai cửa hàng;Cụm ba quán;Chuỗi năm quán;Chuỗi khu vực;Hệ thống café bánh|Lập mẻ nướng, lịch giao, hàng cuối ngày|trạm lò hoặc pha chế
florist|retail|Tiệm hoa lớn;Studio hoa;Trung tâm hoa sự kiện;Hai tiệm;Cụm ba tiệm;Chuỗi năm tiệm;Chuỗi khu vực;Mạng lưới hoa|Nhập theo độ tươi, chia đội trang trí, thu hồi vật liệu|bàn cắm hoa
grocery|retail|Tạp hóa mở rộng;Minimart;Siêu thị mini;Siêu thị khu phố;Cụm ba siêu thị;Chuỗi năm điểm;Chuỗi khu vực;Hệ thống bán lẻ|Giá theo khu, chia ca thu ngân, hạn dùng, đơn sỉ, kho trung tâm|quầy thanh toán
repair|technical|Tiệm có bàn sửa;Xưởng nhỏ;Trung tâm bảo dưỡng;Hai xưởng;Cụm ba xưởng;Chuỗi năm xưởng;Chuỗi khu vực;Mạng lưới kỹ thuật|Chẩn đoán, đặt linh kiện, phân thợ, bảo hành liên điểm|bàn sửa có thợ
farm|farm|Khu trồng mở rộng;Nông trại nhiều khu;Trang trại thương mại;Hai khu sản xuất;Cụm nông trại;Hợp tác sản xuất;Vùng nguyên liệu;Mạng lưới nông nghiệp|Lịch mùa vụ, truy lô, máy móc, hợp đồng đầu ra|tổ khu trồng hoặc chăn nuôi
delivery|logistics|Tổ giao hàng;Điểm giao nhận;Kho phân tuyến;Hai trạm;Cụm ba trạm;Mạng năm trạm;Điều hành khu vực;Mạng lưới giao nhận|Phân tuyến, tải xe, thời hạn, đối soát COD|tổ tuyến có xe
homestay|hospitality|Nhà lưu trú lớn;Nhà nghỉ nhỏ;Khách sạn nhỏ;Hai cơ sở;Cụm ba cơ sở;Chuỗi năm cơ sở;Chuỗi khu vực;Hệ thống lưu trú|Lịch phòng, buồng phòng, đoàn khách, bảo trì|phòng có lịch đặt
pet_care|service|Phòng chăm thú;Trung tâm chăm thú;Khu lưu trú thú;Hai cơ sở;Cụm ba điểm;Chuỗi năm điểm;Chuỗi khu vực;Mạng lưới chăm thú|Lịch chuồng, giới hạn nhân lực, báo cáo và giao nhận|ô chăm thú có người phụ trách
salon|service|Salon lớn;Salon nhiều khu;Salon đào tạo;Hai salon;Cụm ba salon;Chuỗi năm salon;Chuỗi khu vực;Thương hiệu salon|Đặt lịch, chia thợ, mẫu mới, đào tạo và kiểm chất lượng|ghế có thợ
corp_accounting|agency|Kèm nhân viên;Dẫn nhóm sổ;Điều phối kỳ khóa sổ;Hai đơn vị;Cụm đơn vị;Dự án liên phòng;Soát xét khu vực;Chương trình tài chính|Khóa sổ, kiểm chéo, đối chiếu liên đơn vị|nhóm kế toán
tax_payroll|professional|Bàn dịch vụ thuế lương;Văn phòng nhỏ;Trung tâm dịch vụ;Hai nhóm khách;Cụm văn phòng;Chuỗi dịch vụ;Soát xét khu vực;Mạng dịch vụ thuế lương|Lịch chốt lương, bảo mật, đối chiếu theo doanh nghiệp|nhóm hồ sơ
group_accounting|agency|Kèm báo cáo viên;Nhóm hợp nhất;Dự án nhiều công ty;Hai nhóm đơn vị;Cụm hợp nhất;Dự án tập đoàn;Soát xét khu vực;Chương trình báo cáo|Loại trừ nội bộ, kiểm báo cáo, chốt nhiều đơn vị|nhóm hợp nhất
clothing|retail|Shop mở rộng;Boutique;Showroom;Hai cửa hàng;Cụm ba shop;Chuỗi năm shop;Chuỗi khu vực;Thương hiệu thời trang|Mẫu cao cấp, size màu, phân bổ tồn, đổi trả liên tiệm|quầy bán hoặc phòng thử
pet_shop|retail|Tiệm mở rộng;Cửa hàng chuyên thú;Siêu thị đồ thú;Hai cửa hàng;Cụm ba tiệm;Chuỗi năm tiệm;Chuỗi khu vực;Mạng lưới đồ thú|Danh mục theo loài, lô thức ăn, hạn dùng và thu hồi|quầy tư vấn
tra_da|food|Quán nước hợp lệ;Quán giải khát;Quán nhiều khu;Hai quán;Cụm ba quán;Chuỗi năm quán;Chuỗi khu vực;Thương hiệu giải khát|Pha theo mẻ, chỗ ngồi, lịch tiếp bình và vệ sinh|trạm phục vụ
fruit|retail|Sạp trái cây lớn;Cửa hàng trái cây;Trung tâm giỏ quà;Hai cửa hàng;Cụm ba điểm;Chuỗi năm điểm;Chuỗi khu vực;Mạng trái cây sạch|Độ chín, kho lạnh, cân chia, hợp đồng doanh nghiệp|quầy cân hoặc đóng gói
garbage|agency|Kèm tổ viên;Điều phối tuyến;Dự án vệ sinh khu;Hai tổ tuyến;Cụm thu gom;Dự án liên khu;Điều phối khu vực;Chương trình môi trường|Phân tuyến, xe, phân loại, nghiệm thu không bỏ sót|tổ thu gom có xe
drain|technical|Tổ thông cống;Đội có thiết bị;Trung tâm xử lý;Hai đội;Cụm ba đội;Mạng năm đội;Điều phối khu vực;Mạng dịch vụ thoát nước|Khảo sát, chia đội, thiết bị, xử lý và nghiệm thu an toàn|đội có thiết bị
homemaker|service|Nhóm hỗ trợ gia đình;Dịch vụ chăm nhà;Điều phối nhiều nhà;Hai đội;Cụm ba đội;Mạng năm đội;Điều phối khu vực;Mạng dịch vụ gia đình|Lịch nhà, yêu cầu gia đình, phân việc và kiểm tài sản|đội phục vụ gia đình
ice_cream|food|Quầy kem lớn;Tiệm kem;Xưởng kem nhỏ;Hai cửa hàng;Cụm ba tiệm;Chuỗi năm tiệm;Chuỗi khu vực;Thương hiệu kem|Công thức, mẻ lạnh, chuỗi lạnh và lịch cấp hàng|trạm làm hoặc bán kem
nail|service|Tiệm nail lớn;Studio nail;Studio đào tạo;Hai tiệm;Cụm ba tiệm;Chuỗi năm tiệm;Chuỗi khu vực;Thương hiệu nail|Mẫu mới, lịch thợ, khử khuẩn, phản hồi khách|bàn có thợ
pagoda|community|Tham gia công quả;Phụ trách việc nhỏ;Điều phối buổi công quả;Phối hợp hai nhóm;Dự án cộng đồng;Chương trình nhiều điểm;Điều phối liên nhóm;Truyền kinh nghiệm công quả|Giúp khách, chia việc thiện, giữ riêng tư thẻ chúc; không bán công đức|nhóm tình nguyện
pho|food|Quán phở lớn;Nhà hàng phở;Bếp nước dùng;Hai quán;Cụm ba quán;Chuỗi năm quán;Chuỗi khu vực;Thương hiệu phở|Nấu mẻ bằng nguyên liệu thật, chia bếp, kiểm nước dùng|trạm bếp
com|food|Quán cơm lớn;Cửa hàng cơm;Bếp suất ăn;Hai cơ sở;Cụm ba bếp;Chuỗi năm cơ sở;Chuỗi khu vực;Hệ thống suất ăn|Khẩu phần, hợp đồng, lịch giao và giữ nóng|trạm bếp
photobooth|arts|Góc chụp lớn;Studio nhỏ;Studio sự kiện;Hai studio;Cụm ba điểm;Chuỗi năm điểm;Chuỗi khu vực;Thương hiệu ảnh|Lịch máy, phân người chụp, chỉnh ảnh, bàn giao|buồng chụp hoặc bàn xử lý
giupviec|service|Tổ giúp việc;Dịch vụ vệ sinh;Trung tâm điều phối;Hai đội;Cụm ba đội;Mạng năm đội;Điều phối khu vực;Mạng vệ sinh|Lịch nhiều nhà, dụng cụ, nghiệm thu và tài sản|đội có dụng cụ
naucom|food|Nhóm bếp gia đình;Dịch vụ bếp nhà;Bếp đặt theo lịch;Hai đội bếp;Cụm ba đội;Mạng năm đội;Điều phối khu vực;Mạng bếp gia đình|Thực đơn theo nhà, dị ứng, giờ giao và phân bếp|đội bếp
babysitter|service|Nhóm bảo mẫu;Dịch vụ chăm trẻ;Trung tâm điều phối;Hai nhóm;Cụm ba nhóm;Mạng năm nhóm;Điều phối khu vực;Mạng chăm trẻ|Lịch giao nhận, nhân lực đúng ca, báo cáo và giám sát|nhóm có người giám sát
library|agency|Kèm thủ thư;Phụ trách khu sách;Dự án thư viện;Hai nhóm;Cụm thư viện;Chương trình liên điểm;Điều phối khu vực;Mạng chia sẻ tư liệu|Phân công lưu trữ, chuyển sách, bảo quản và lịch phục vụ|nhóm nghiệp vụ
pilot|agency|Hỗ trợ huấn luyện;Kèm tổ bay;Dự án điều phối;Hai tổ bay;Cụm tổ bay;Chương trình huấn luyện;Phối hợp khu vực;Chương trình khai thác|Kế hoạch bay, thời tiết, nghỉ tổ bay; giữ chứng chỉ và chức danh|tổ bay đủ điều kiện
flight_attendant|agency|Kèm tiếp viên;Điều phối phục vụ;Dự án chất lượng;Hai tổ;Cụm tổ;Chương trình huấn luyện;Phối hợp khu vực;Chương trình dịch vụ|Lịch tổ, suất ăn, nhu cầu khách và kiểm an toàn|tổ tiếp viên
oil|agency|Kèm kỹ thuật viên;Điều phối tổ;Dự án bảo dưỡng;Hai tổ;Cụm tổ;Dự án nhiều khu;Phối hợp khu vực;Chương trình vận hành|Giấy phép công việc, lịch bảo dưỡng, cô lập thiết bị|tổ kỹ thuật
hr_admin|agency|Kèm nhân viên;Điều phối nhóm;Dự án nhân sự;Hai bộ phận;Cụm bộ phận;Chương trình liên đơn vị;Điều phối khu vực;Chương trình nhân sự|Phân việc, tuyển dụng, lịch làm và bảo mật|nhóm nhân sự
secretary|agency|Kèm trợ lý;Điều phối lịch;Dự án văn phòng;Hai nhóm;Cụm nhóm;Chương trình liên đơn vị;Phối hợp khu vực;Chương trình điều hành|Lịch họp, quyền xem, theo dõi đầu việc và bàn giao|nhóm trợ lý
it_helpdesk|agency|Kèm kỹ thuật viên;Điều phối hỗ trợ;Dự án hệ thống;Hai nhóm;Cụm nhóm;Dự án liên đơn vị;Điều phối khu vực;Chương trình dịch vụ IT|Chia ticket, quyền truy cập, khôi phục và nghiệm thu|nhóm hỗ trợ IT
railway|agency|Kèm ca trực;Điều phối tổ;Dự án kiểm tra;Hai điểm;Cụm điểm;Chương trình liên tuyến;Phối hợp khu vực;Chương trình an toàn|Bố trí người, kiểm thiết bị và bàn giao ca; không tăng tải an toàn|tổ có người trực
nurse|agency|Kèm điều dưỡng;Điều phối nhóm;Dự án chăm sóc;Hai nhóm;Cụm nhóm;Chương trình liên khoa;Phối hợp khu vực;Chương trình chất lượng|Lịch chăm, giao ca, kiểm thuốc và báo bác sĩ|nhóm điều dưỡng
lighthouse|agency|Kèm ca trực;Điều phối tổ đèn;Dự án bảo dưỡng;Hai điểm;Cụm điểm;Chương trình tuyến biển;Phối hợp khu vực;Chương trình tín hiệu|Vật tư, lịch trực, tín hiệu dự phòng và kiểm đèn|tổ trực đèn
rescue|agency|Kèm điện thoại viên;Điều phối ca;Dự án phản ứng;Hai tổ;Cụm tổ;Chương trình liên trạm;Phối hợp khu vực;Chương trình cứu hộ|Phân loại cuộc gọi, điều đội, bàn giao và hậu kiểm|tổ tổng đài
lifeguard|agency|Kèm nhân viên;Điều phối ca;Dự án an toàn hồ;Hai tổ;Cụm hồ;Chương trình liên điểm;Phối hợp khu vực;Chương trình cứu hộ nước|Phân vùng quan sát, bố trí người và diễn tập|tổ giám sát
police|agency|Kèm nghiệp vụ;Phối hợp tổ;Chuyên đề địa bàn;Phối hợp hai tổ;Chuyên đề liên tổ;Dự án liên địa bàn;Phối hợp khu vực;Chương trình nghiệp vụ|Giao hồ sơ, kiểm bằng chứng, đề nghị khen; chức vụ qua luật hiện hành|tổ nghiệp vụ
zpop|retail|Tiệm album lớn;Cửa hàng chuyên nhạc;Showroom fan goods;Hai cửa hàng;Cụm ba tiệm;Chuỗi năm tiệm;Chuỗi khu vực;Mạng lưới album|Bản hiếm, preorder có cọc, phân tồn và đối soát|quầy bán hoặc nhận hàng
art_studio|arts|Xưởng vẽ lớn;Studio;Gallery và xưởng;Hai studio;Cụm ba điểm;Chuỗi năm điểm;Chuỗi khu vực;Mạng lưới nghệ thuật|Hợp đồng tranh, vật liệu, phân họa sĩ và triển lãm|bàn vẽ hoặc khu trưng bày
lawyer|professional|Bàn tư vấn;Văn phòng luật;Hãng luật nhỏ;Hai nhóm hồ sơ;Cụm văn phòng;Hãng nhiều chi nhánh;Điều phối khu vực;Mạng lưới hãng luật|Phân hồ sơ, xung đột lợi ích, thời hạn và nghiệm thu; không bảo đảm thắng kiện|nhóm luật sư đủ điều kiện
laundry|service|Tiệm giặt lớn;Tiệm nhiều máy;Xưởng giặt;Hai cơ sở;Cụm ba điểm;Chuỗi năm điểm;Chuỗi khu vực;Mạng giặt và giao nhận|Máy có chu kỳ, chia đồ, lịch giao, đồ thất lạc và bảo trì|máy có lịch chạy
restore|service|Xưởng phục chế lớn;Xưởng nhiều bàn;Xưởng phục chế có kho;Hai xưởng;Cụm ba xưởng;Chuỗi năm xưởng;Chuỗi khu vực;Mạng phục chế đồ xưa|Khám đồ, chốt yêu cầu khách, linh kiện chế lại, ảnh trước sau|bàn phục hồi
post_office|agency|Kèm giao dịch viên;Điều phối quầy;Dự án bưu cục;Hai tổ;Cụm bưu cục;Chương trình liên tuyến;Điều phối khu vực;Chương trình bưu chính|Chia tuyến, phân kiện, COD, thời hạn và hàng hoàn|tổ bưu chính
customs|agency|Kèm kiểm tra viên;Phối hợp đội;Chuyên đề luồng hàng;Phối hợp hai đội;Chuyên đề liên đội;Dự án liên cửa khẩu;Phối hợp khu vực;Chương trình kiểm soát hải quan|Phân luồng, kiểm hóa, thuế, hàng tạm giữ; chức vụ qua bổ nhiệm|đội nghiệp vụ
banquet|agency|Kèm bếp trưởng;Phụ trách một bếp;Dự án mùa cưới;Hai ca phối hợp;Cụm nhà hàng tiệc;Chương trình liên cơ sở;Điều phối khu vực;Chương trình ẩm thực tiệc|Phiếu tiệc, sơ chế, ra món, sảnh sự kiện, vệ sinh và an toàn điện|ca bếp và sảnh
reception|agency|Kèm trưởng ca;Trực một quầy;Dự án mùa đoàn;Hai ca phối hợp;Cụm khách sạn nhỏ;Chương trình liên cơ sở;Điều phối khu vực;Chương trình lễ tân của phố|Bảng phòng, chìa, hành lý, lịch dọn phòng, lịch dịch vụ, phàn nàn và đồ thất lạc|ca quầy lễ tân
teller|agency|Kèm trưởng quầy;Phụ trách một quầy;Dự án mùa lương hưu;Hai quầy phối hợp;Cụm phòng giao dịch;Chương trình liên chi nhánh;Điều phối khu vực;Chương trình ngân hàng bán lẻ|Khay tiền, đối chiếu người nhận, tiết kiệm mục tiêu, quỹ ATM và bàn giao quỹ|quầy giao dịch
hotel|agency|Kèm trưởng ca;Điều phối một tầng;Dự án mùa lễ;Hai ca phối hợp;Cụm khách sạn;Chương trình liên cơ sở;Điều phối khu vực;Chương trình vận hành lưu trú|Bảng phòng, buồng phòng, giặt là, bữa sáng, bảo trì và mùa lễ|ca vận hành
research|agency|Kèm nghiên cứu viên chính;Phụ trách một thí nghiệm;Đề tài cấp viện;Hai nhóm phối hợp;Cụm phòng thí nghiệm;Chương trình liên viện;Điều phối khu vực;Chương trình nghiên cứu ứng dụng|Giống cây, công thức món, mẫu sáng chế, hội đồng khoa học và an toàn phòng thí nghiệm|nhóm nghiên cứu
radio|agency|Kèm trưởng đài;Phụ trách một chương trình;Dự án mùa lễ;Hai ca phối hợp;Cụm đài phường;Chương trình liên đài;Điều phối khu vực;Chương trình phát thanh cộng đồng|Bản tin, quảng cáo duyệt, ca nhạc theo yêu cầu, cuộc gọi vào sóng và sự cố kỹ thuật|ca phát sóng'''


def _build_profiles() -> Mapping[str, Profile]:
    authored = {row.split('|', 1)[0]: row.split('|')[1:]
                for row in _AUTHORED.splitlines()}
    supplies = {row.split('|', 1)[0]: row.split('|')[1:]
                for row in _SUPPLIES.splitlines()}
    profiles = {}
    for row in _SCOPES.splitlines():
        cid, group, titles, focus, resource = row.split('|')
        roles, name, unit, bundle, quality, *details = authored[cid]
        phase_pairs, records = details[:4], tuple(details[4].split(';'))
        phases = []
        for index, pair in enumerate(phase_pairs):
            full, incomplete = pair.split('~')
            # IDs identify alternatives, not correctness; rotate the successful
            # alternative across careers/phases to avoid an always-A key.
            options = ((full, 100), (incomplete, 0))
            if (sum(map(ord, cid)) + index) % 2:
                options = tuple(reversed(options))
            phases.append(tuple(Choice(chr(97 + n), label, records[index], score)
                                for n, (label, score) in enumerate(options)))
        scenario = Scenario(f'{name}: điều phối và bàn giao', *phases, records)
        supply, base_unit, batch = supplies[cid]
        material = Material(f'{cid}_supply', supply, base_unit, bundle, quality,
                            1, int(batch), name, unit)
        kind = group if group in ('agency', 'community') else 'business'
        factor = _GROUPS[group][0]
        stages = tuple(Stage(
            i + 1, title, _FEES[i] * factor // 10, _SITES[i], _RESOURCES[i],
            _NET[i] // 4 if kind == 'agency' else _NET[i] * factor // 10,
            _DAYS[i], _CLEAN[i],
        ) for i, title in enumerate(titles.split(';')))
        profiles[cid] = Profile(cid, kind, group, resource,
                                tuple(roles.split(';')), (material,), stages,
                                scenario, focus)
    return MappingProxyType(profiles)


PROFILES = _build_profiles()


def profile(cid: str) -> Profile:
    """Return server-only immutable content, including choice evaluation data."""
    return PROFILES[cid]


def stage(cid: str, tier: int) -> Stage:
    """Return a stage from 1 to 8; tier zero belongs to the existing career."""
    if type(tier) is not int or not 1 <= tier <= 8:
        raise ValueError('Bậc quy mô phải là số nguyên từ 1 đến 8.')
    return profile(cid).stages[tier - 1]


def stage_dict(cid: str, tier: int) -> dict:
    """Return a detached public stage DTO."""
    return asdict(stage(cid, tier))


def profile_dict(cid: str) -> dict:
    """Public JSON-ready DTO; never expose scores or resolution evidence.

    Tuple fields are JSON arrays when serialized. Callers must use the raw
    server-only ``profile`` for evaluation, not accept scores from clients.
    """
    result = asdict(profile(cid))
    result['scenario'].pop('evidence')
    for phase in ('planning', 'allocation', 'exception', 'acceptance'):
        result['scenario'][phase] = tuple(
            {'id': option['id'], 'label': option['label']}
            for option in result['scenario'][phase])
    return result


def _ceil(value: Fraction) -> int:
    return -(-value.numerator // value.denominator)


def _nearest(value: Fraction) -> int:
    return (value + Fraction(1, 2)).numerator // (value + Fraction(1, 2)).denominator


def _costs_at_full(s: Stage, group: str) -> tuple[Fraction, tuple[Fraction, ...]]:
    _, goods, wage, rent, loss, tax = _GROUPS[group]
    full = Fraction(s.net * 100, 100 - goods - wage - rent - loss - tax)
    return full, (full * goods / 100, full * wage * Fraction(3, 500),
                  full * wage * Fraction(2, 500), full * rent / 100,
                  full * loss / 100, full * tax / 100)


def _reconcile(exact: tuple[Fraction, ...], total: int) -> tuple[int, ...]:
    """Largest-remainder costs preserve the rounded net and integer receipt."""
    values = [v.numerator // v.denominator for v in exact]
    remainder = total - sum(values)
    order = sorted(range(len(exact)),
                   key=lambda i: exact[i] - values[i], reverse=True)
    # Revenue rounds up and net rounds nearest, so total may exceed the
    # floor sum by at most the number of categories (including a zero tie).
    if not 0 <= remainder <= len(values):
        raise ArithmeticError('Không thể đối soát các khoản chi phí.')
    for index in order[:remainder]:
        values[index] += 1
    return tuple(values)


def _procurement(p: Profile, s: Stage, consumed_cost: int, demand: int) -> list[dict]:
    m = p.materials[0]
    funded_by = 'business' if p.kind == 'business' else (
        'organization' if p.kind == 'agency' else 'community')
    # Organizational/community supplies are an in-kind allocation plan, never
    # a player expense, cash allowance or withdrawable account balance.
    consumed = consumed_cost // m.unit_cost if p.kind == 'business' else (
        s.resources * m.batch_units * demand // 100)
    packs = (consumed + m.batch_units - 1) // m.batch_units
    purchased = packs * m.batch_units
    remaining = purchased - consumed
    return [dict(code=m.code, name=m.name, unit=m.unit, unit_cost=m.unit_cost,
                 batch_units=m.batch_units, quantity=packs,
                 purchased_units=purchased, consumed_units=consumed,
                 remaining_units=remaining, purchase_cost=purchased * m.unit_cost,
                 consumed_cost=consumed * m.unit_cost, carry_value=remaining * m.unit_cost,
                 units_per_resource=(consumed + s.resources - 1) // s.resources,
                 funded_by=funded_by)]


def quote(cid: str, tier: int, demand: int = 100) -> dict:
    """Quote one whole-network session with an exactly reconciled xu ledger.

    ``materials`` is CONSUMED cost, not procurement cash. ``material_plan``
    separately records full-pack purchases and physical stock still held at
    its original unit cost. Its agency/community allocations are in kind.
    A quote is a forecast; it does not spend money, stock, or a daily slot.
    Cost percentages are final experimental prices with a single tax reserve;
    settlement must reconcile actual invoices against that reserve once.
    """
    if type(demand) is not int or not 0 <= demand <= 100:
        raise ValueError('Nhu cầu phải là số nguyên từ 0 đến 100%.')
    p, s = profile(cid), stage(cid, tier)
    d = Fraction(demand, 100)
    if p.kind == 'business':
        full, at_full = _costs_at_full(s, p.group)
        exact = tuple(v if i in (2, 3) else v * d
                      for i, v in enumerate(at_full))
        revenue = _ceil(full * d)
        net = _nearest(full * d - sum(exact))
        goods, variable, fixed, premises, loss, tax = _reconcile(exact, revenue - net)
    else:
        revenue = net = _nearest(s.net * d)
        goods = variable = fixed = premises = loss = tax = 0
    wages = variable + fixed
    result = dict(cid=cid, tier=tier, demand=demand, kind=p.kind,
                  revenue=revenue, materials=goods, wages=wages,
                  wage_variable=variable, wage_fixed=fixed,
                  premises=premises, loss=loss, tax=tax, net=net,
                  cost_total=goods + wages + premises + loss + tax,
                  fee=s.fee, sites=s.sites, resources=s.resources)
    result['material_plan'] = _procurement(p, s, goods, demand)
    return result
