"""Reproducible DESIGN estimates; never imports a DB or changes game rules.

Run from the repository root. All proposed prices are final displayed xu.
Outputs a 54-career inventory and 432 career/stage economic scenarios.
"""
from pathlib import Path
from decimal import Decimal, ROUND_CEILING
import csv
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from game.content import CAREERS, CAREER_META

OUT = Path(__file__).resolve().parent
PRICES = [50_000, 250_000, 1_000_000, 4_000_000, 12_000_000, 35_000_000, 100_000_000, 250_000_000]
NET = [1_000, 3_500, 12_000, 35_000, 90_000, 200_000, 420_000, 800_000]
SITES = [1, 1, 1, 2, 3, 5, 8, 12]
STATIONS = [2, 4, 6, 10, 16, 24, 36, 50]
DAYS = [3, 7, 14, 30, 60, 100, 160, 240]
CASES = [10, 30, 70, 140, 260, 450, 750, 1200]
# factor; direct goods; wages; premises/utilities; expected loss; tax reserve.
# 60% of wages vary with demand, 40% are fixed for a started session.
GROUPS = {
 'retail': ('Bán lẻ', '1', 70, 8, 4, 2, 4),
 'food': ('Ẩm thực', '.8', 55, 18, 8, 3, 4),
 'service': ('Dịch vụ', '.7', 35, 25, 12, 3, 4),
 'technical': ('Kỹ thuật', '1.2', 50, 20, 10, 3, 4),
 'farm': ('Nông nghiệp', '1.2', 50, 18, 12, 4, 4),
 'hospitality': ('Lưu trú', '1.5', 25, 30, 20, 3, 4),
 'professional': ('Dịch vụ hồ sơ', '.6', 20, 35, 12, 2, 4),
 'arts': ('Nghệ thuật', '.8', 40, 25, 12, 3, 4),
 'logistics': ('Vận chuyển', '1.2', 55, 20, 10, 3, 4),
 'agency': ('Cơ quan / làm công', '0', 0, 0, 0, 0, 0),
 'community': ('Công quả', '0', 0, 0, 0, 0, 0),
}

# Exact IDs are checked against the executable career registry below.
# Eight stages describe project scope, NOT automatically granted job titles.
DATA = '''mother_baby|retail|Tiệm chuyên đồ sơ sinh;Cửa hàng mẹ bé;Trung tâm mẹ bé;Hai cửa hàng;Cụm ba tiệm;Chuỗi năm tiệm;Chuỗi khu vực;Mạng lưới mẹ bé|Tư vấn theo tuổi, truy lô, đổi trả liên điểm|quầy tư vấn
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
post_office|agency|Kèm giao dịch viên;Điều phối quầy;Dự án bưu cục;Hai tổ;Cụm bưu cục;Chương trình liên tuyến;Điều phối khu vực;Chương trình bưu chính|Chia tuyến, phân kiện, COD, thời hạn và hàng hoàn|tổ bưu chính'''


def ceil(x):
    return int(x.to_integral_value(rounding=ROUND_CEILING))


def fmt(x):
    return f'{x:,.0f}'.replace(',', '.')


def run():
    rows = [line.split('|') for line in DATA.splitlines()]
    assert len(rows) == len(CAREERS) == 54
    assert {r[0] for r in rows} == set(CAREERS)
    assert all(len(r) == 5 and len(r[2].split(';')) == 8 for r in rows)
    scenarios = []
    catalogue = ['# Lộ trình đủ 54 nghề — đề xuất 14/10/2026', '',
                 'Tên bậc cơ quan là phạm vi dự án; không tự trao chức vụ. Giá xem bảng nhóm và CSV. Tài nguyên là tổng mạng lưới, không nhân tiếp số cơ sở.', '',
                 '| Nghề / ID | Nhóm | Tám mốc từ thấp đến cao | Việc quản lý mới | Tài nguyên thực |',
                 '|---|---|---|---|---|']
    for cid, group, titles, gameplay, unit in rows:
        label, factor, goods, wages, premises, loss, tax = GROUPS[group]
        factor = Decimal(factor)
        previous = previous80 = Decimal(0)
        paid = 0
        catalogue.append(f'| {CAREER_META[cid]["short"]} (`{cid}`) | {label} | {" → ".join(titles.split(";"))} | {gameplay} | {unit} |')
        for i, title in enumerate(titles.split(';')):
            fee = int(PRICES[i] * factor)
            paid += fee
            target = Decimal(NET[i]) * (Decimal('.25') if group == 'agency' else factor)
            if group in ('agency', 'community'):
                revenue = target
                costs = Decimal(0)
                net80 = target * Decimal('.8')
                net60 = target * Decimal('.6')
                var = fixed = break_even = Decimal(0)
            else:
                margin = Decimal(100 - goods - wages - premises - loss - tax) / 100
                revenue = target / margin
                var = (Decimal(goods + loss + tax) + Decimal(wages) * Decimal('.6')) / 100
                fixed = (Decimal(premises) + Decimal(wages) * Decimal('.4')) / 100
                assert var + fixed + margin == 1
                costs = revenue - target
                net80 = revenue * (Decimal('.8') * (1-var) - fixed)
                net60 = revenue * (Decimal('.6') * (1-var) - fixed)
                break_even = fixed / (1-var)
            delta = target-previous
            delta80 = net80-previous80
            scenarios.append(dict(career=cid, name=CAREER_META[cid]['short'], group=group,
                stage=i+1, title=title, expansion_fee_xu=fee, cumulative_expansion_xu=paid,
                qualified_real_days=DAYS[i], clean_cases=CASES[i],
                coordinated_sites=SITES[i], total_resource_slots=STATIONS[i], resource_unit=unit,
                revenue_at_full=ceil(revenue), operating_cost_at_full=ceil(costs), net_at_full=int(target),
                net_at_80_percent=round(net80, 2), net_at_60_percent=round(net60, 2),
                break_even_demand_pct=round(break_even*100, 2),
                cash_reserve_two_full_sessions=ceil(costs*2),
                marginal_payback_sessions_full=round(Decimal(fee)/delta, 2) if fee and delta>0 else '',
                marginal_payback_sessions_80=round(Decimal(fee)/delta80, 2) if fee and delta80>0 else '',
                net_four_sessions_full=int(target*4),
                scope='proposed_new_management_only'))
            previous, previous80 = target, net80
    with (OUT/'economy.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer=csv.DictWriter(f, fieldnames=scenarios[0]); writer.writeheader(); writer.writerows(scenarios)
    (OUT/'careers.md').write_text('\n'.join(catalogue)+'\n', encoding='utf-8', newline='\n')
    summary = ['# Bảng kinh tế đề xuất — 14/10/2026', '',
               'Một ca quản lý là gói hợp đồng/việc có nhiều bước, dự kiến 10–20 phút thao tác; không phải một lần nhấn. Tối đa 4 suất/ngày thực dùng chung tài khoản. Các con số không phải lợi nhuận đang chạy trên máy chủ.', '',
               '## Tạp hóa', '',
               '| Bậc | Phí lên bậc | Tổng phí quy mô | Điểm điều phối | Tổng vị trí | Lãi ca đầy / 80% nhu cầu | Quỹ dự phòng hai ca đầy | Hoàn phí tăng thêm: ca đầy / 80% |',
               '|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in scenarios:
        if r['career']=='grocery':
            summary.append(f'| {r["stage"]} | {fmt(r["expansion_fee_xu"])} | {fmt(r["cumulative_expansion_xu"])} | {r["coordinated_sites"]} | {r["total_resource_slots"]} | {fmt(r["net_at_full"])} / {fmt(r["net_at_80_percent"])} | {fmt(r["cash_reserve_two_full_sessions"])} | {r["marginal_payback_sessions_full"]} / {r["marginal_payback_sessions_80"]} |')
    summary += ['', '## Giá từng nhóm kinh doanh', '',
                '| Nhóm (số nghề) | Phí lần lượt bậc 1–8 | Tổng quy mô | Lãi ca đầy bậc 8 |',
                '|---|---|---:|---:|']
    for group, (label, factor, *_) in GROUPS.items():
        if group in ('agency','community'):continue
        factor=Decimal(factor)
        count=sum(r[1]==group for r in rows)
        summary.append(f'| {label} ({count}) | {" → ".join(fmt(Decimal(x)*factor) for x in PRICES)} | {fmt(Decimal(sum(PRICES))*factor)} | {fmt(Decimal(NET[-1])*factor)} |')
    summary += ['', '19 nghề cơ quan không thu vốn mở cơ sở. Phụ cấp quản lý mục tiêu bậc 1–8: 250 / 875 / 3.000 / 8.750 / 22.500 / 50.000 / 105.000 / 200.000 xu mỗi ca được nghiệm thu đầy đủ. Học phí nội dung và công cụ cá nhân là các khoản riêng, không mua chức vụ.', '',
                'Chùa có 8 mốc công quả, không thu phí quy mô và không tạo lợi nhuận chuỗi mới. Giữ các quyền và phần thưởng hiện có.', '',
                '## Thành phần chi phí khi đầy nhu cầu', '',
                '| Nhóm | Hàng/vật tư | Lương | Mặt bằng/điện/bảo trì | Hao hụt dự phòng | Thuế doanh thu | Biên ròng | Hòa vốn ở nhu cầu | Lãi 80% / lãi đầy |',
                '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for group, (label, factor, goods, wages, premises, loss, tax) in GROUPS.items():
        if group in ('agency','community'):continue
        r=next(r for r in scenarios if r['group']==group and r['stage']==8)
        ratio=Decimal(r['net_at_80_percent'])/Decimal(r['net_at_full'])*100
        summary.append(f'| {label} | {goods}% | {wages}% | {premises}% | {loss}% | {tax}% | {100-goods-wages-premises-loss-tax}% | {r["break_even_demand_pct"]}% | {ratio:.2f}% |')
    (OUT/'economy-summary.md').write_text('\n'.join(summary)+'\n', encoding='utf-8', newline='\n')
    assert len(scenarios)==432
    assert sum(PRICES)==402_300_000
    print('Coverage:',len(rows),'careers;',len(scenarios),'scenarios')
    for group in GROUPS:
        count=sum(r[1]==group for r in rows)
        print(group,count,'total capital',fmt(Decimal(sum(PRICES))*Decimal(GROUPS[group][1])))
    print('GROCERY: stage; fee; total; net; net80; reserve; payback full/80 sessions')
    for r in scenarios:
        if r['career']=='grocery':
            print(r['stage'],r['expansion_fee_xu'],r['cumulative_expansion_xu'],r['net_at_full'],
                  r['net_at_80_percent'],r['cash_reserve_two_full_sessions'],
                  r['marginal_payback_sessions_full'],r['marginal_payback_sessions_80'])


if __name__ == '__main__':
    run()
