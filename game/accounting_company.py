"""A connected, fictional Vietnamese manufacturing/trading company's 2026 book.

Amounts are VND. Taxes, payroll charges and tax adjustments come from supplied
source schedules: TT99 governs their accounting, not their tax determination.
Correct entries post once; statements reconcile the same book. No AI grading.
"""
from __future__ import annotations

from functools import lru_cache
from . import procedures
from .jsoncopy import tree_copy

SOURCE = 'https://congbao.chinhphu.vn/van-ban/thong-tu-so-99-2025-tt-btc-46529.htm'
NAME = 'Công ty CP Mây Tre Xanh'
CHART = dict([
    ('111', 'Tiền mặt'), ('112', 'Tiền gửi không kỳ hạn'), ('1281', 'Tiền gửi có kỳ hạn'),
    ('131', 'Phải thu của khách hàng'), ('1331', 'Thuế GTGT được khấu trừ của hàng hóa, dịch vụ'),
    ('1332', 'Thuế GTGT được khấu trừ của tài sản cố định'),
    ('152', 'Nguyên liệu, vật liệu'), ('154', 'Chi phí sản xuất, kinh doanh dở dang'),
    ('155', 'Sản phẩm'), ('156', 'Hàng hóa'), ('211', 'Tài sản cố định hữu hình'),
    ('214', 'Hao mòn tài sản cố định'), ('2293', 'Dự phòng phải thu khó đòi'),
    ('242', 'Chi phí chờ phân bổ'), ('243', 'Tài sản thuế thu nhập hoãn lại'),
    ('331', 'Phải trả cho người bán'), ('332', 'Phải trả cổ tức, lợi nhuận'),
    ('3331', 'Thuế GTGT phải nộp'), ('3334', 'Thuế thu nhập doanh nghiệp'),
    ('334', 'Phải trả người lao động'), ('3383', 'Bảo hiểm xã hội'),
    ('3387', 'Doanh thu chờ phân bổ'), ('341', 'Vay và nợ thuê tài chính'),
    ('347', 'Thuế thu nhập hoãn lại phải trả'), ('411', 'Vốn đầu tư của chủ sở hữu'),
    ('4211', 'Lợi nhuận sau thuế chưa phân phối lũy kế đến cuối năm trước'), ('4212', 'Lợi nhuận sau thuế chưa phân phối năm nay'),
    ('511', 'Doanh thu bán hàng và cung cấp dịch vụ'), ('515', 'Doanh thu hoạt động tài chính'),
    ('521', 'Các khoản giảm trừ doanh thu'), ('621', 'Chi phí nguyên liệu, vật liệu trực tiếp'),
    ('622', 'Chi phí nhân công trực tiếp'), ('627', 'Chi phí sản xuất chung'),
    ('632', 'Giá vốn hàng bán'), ('635', 'Chi phí tài chính'), ('641', 'Chi phí bán hàng'),
    ('642', 'Chi phí quản lý doanh nghiệp'), ('8211', 'Chi phí thuế thu nhập doanh nghiệp hiện hành'),
    ('8212', 'Chi phí thuế thu nhập doanh nghiệp hoãn lại'), ('911', 'Xác định kết quả kinh doanh'),
])
OPENING = {'111': 10_000_000, '112': 100_000_000, '131': 12_000_000, '152': 8_000_000,
           '155': 10_000_000, '211': 80_000_000, '214': -20_000_000, '331': -15_000_000,
           '341': -30_000_000, '411': -140_000_000, '4211': -15_000_000}
OPEN_DEBTS = {'131|khach_cu': 12_000_000, '331|ncc_cu': -15_000_000}


def initial() -> dict:
    return dict(period=1, at=0, inspected=[], answers={}, mistakes=0, paid=False,history={})


def _need(ok, message):
    from .engine import need
    need(ok, message)


def _n(amount):
    return f'{amount:,}'.replace(',', '.') + ' đồng'


@lru_cache(maxsize=12)
def _transactions(period: int) -> list:
    factor = 10 + (period - 1) % 3
    def amount(v): return v * factor // 10
    allocation = sum(200_000 * (10 + (p - 1) % 3) // 10 for p in range(1,period+1))
    production_dep = 500_000 + sum(300_000 * (10 + (p - 1) % 3) // 10 for p in range(1,period+1))
    production_overhead = amount(1_000_000) + production_dep
    production_total = amount(12_800_000) + production_overhead
    service_revenue = sum(2_000_000 * (10 + (p - 1) % 3) // 10 for p in range(max(1,period-2),period+1))
    rows = []
    def add(sid, title, entries, source, explain, activity=None, party=None, closing=False, scaled=True):
        lines = [dict(debit=d, credit=c, amount=amount(a) if scaled else a) for d, c, a in entries]
        text = source.format(**{f'n{i}': _n(line['amount']) for i, line in enumerate(lines)})
        codes = sorted({x for line in lines for x in (line['debit'], line['credit'])})
        rows.append(dict(id=sid, title=title, kind='entry', prompt='Đọc chứng từ rồi lập các dòng Nợ/Có bằng VND.',
                         _key=lines, explain=explain, activity=activity, party=party, closing=closing,
                         docs=[dict(id=sid + '_source', title=title + ' · chứng từ gốc', lines=[text])],
                         accounts=[dict(id=a, name=name) for a, name in CHART.items()],
                         references=[dict(label='Thông tư 99/2025/TT-BTC', url=SOURCE,
                                          locator='Phụ lục II – ' + ', '.join('TK ' + c for c in codes))]))
    add('capital', 'Góp thêm vốn bằng chuyển khoản', [('112','411',50_000_000)],
        'Ngân hàng báo Có {n0}; nghị quyết và hồ sơ góp vốn đã hoàn tất, không phải khoản vay.',
        'Tiền gửi không kỳ hạn tăng bên Nợ 112; vốn đầu tư của chủ sở hữu tăng bên Có 411.', 'financing')
    add('materials', 'Nhập nguyên liệu mua chịu', [('152','331',12_000_000),('1331','331',1_200_000)],
        'Phiếu nhập kho: nguyên liệu chưa thuế {n0}. Hóa đơn và bảng soát xét thuế xác nhận GTGT đầu vào được khấu trừ {n1}. Chưa trả nhà cung cấp cũ.',
        'Giá mua nguyên liệu ghi 152; thuế đầu vào đủ điều kiện ghi 1331; tổng nghĩa vụ ghi Có 331. Không đưa thuế được khấu trừ vào giá kho.', party='ncc_cu')
    add('supplier_pay', 'Trả nợ nhà cung cấp nguyên liệu', [('331','112',8_000_000)],
        'Ủy nhiệm chi và báo Nợ {n0}, thanh toán nhà cung cấp cũ.', 'Giảm khoản phải trả 331 và tiền gửi 112; hoạt động kinh doanh.', 'operating','ncc_cu')
    add('supplier_advance', 'Ứng trước cho nhà cung cấp mới', [('331','112',2_000_000)],
        'Chuyển {n0} cho nhà cung cấp mới ncc_truoc; chưa nhận hàng, chưa có nghĩa vụ thuế đầu vào.',
        'Ứng trước tạo số dư Nợ chi tiết 331. Khi trình bày B01 phải tách khỏi số dư Có của nhà cung cấp khác.', 'operating','ncc_truoc')
    add('cash_withdrawal', 'Rút tiền gửi bổ sung quỹ tiền mặt', [('111','112',5_000_000)],
        'Báo Nợ ngân hàng và phiếu thu xác nhận rút {n0} vào quỹ; thủ quỹ đã kiểm nhận.',
        'Chuyển từ112 sang111, không làm tăng/giảm tổng tiền, không là một dòng tiền kinh doanh/đầu tư/tài chính.')
    add('cash_transfer', 'Nộp tiền mặt vào ngân hàng', [('112','111',2_000_000)],
        'Phiếu chi và giấy nộp tiền {n0}; ngân hàng đã ghi Có tài khoản không kỳ hạn.',
        'Chuyển giữa tiền mặt và tiền gửi: tổng tiền không đổi, không là dòng tiền từ kinh doanh/đầu tư/tài chính.')
    add('goods', 'Mua hàng hóa bằng tiền mặt', [('156','111',4_000_000),('1331','111',400_000)],
        'Hàng mua về để bán: giá chưa thuế {n0}, thuế đầu vào đủ điều kiện {n1}; đã trả bằng tiền mặt.',
        'Hàng để bán ghi 156, thuế được khấu trừ ghi 1331, giảm tiền mặt tổng số đã trả.', 'operating')
    add('customer_advance', 'Khách hàng mới trả trước', [('112','131',5_000_000)],
        'Khách khach_dat chuyển {n0} đặt mua hàng, công ty chưa giao sản phẩm và chưa ghi doanh thu.',
        'Có chi tiết 131 của khach_dat là người mua trả tiền trước; không bù với khách khác còn nợ.', 'operating','khach_dat')
    add('old_receipt', 'Thu công nợ đầu kỳ', [('112','131',12_000_000)],
        'Ngân hàng báo Có {n0} từ khach_cu thanh toán công nợ đang theo dõi; tháng1 là hóa đơn đầu năm, các tháng sau là các hóa đơn còn nợ trong sổ chi tiết.', 'Thu nợ chỉ giảm131, không ghi doanh thu lần thứ hai.', 'operating','khach_cu')
    add('machine', 'Mua máy đã nghiệm thu đưa vào sử dụng', [('211','331',36_000_000),('1332','331',3_600_000)],
        'Máy đủ tiêu chuẩn TSCĐ, sẵn sàng sử dụng. Nguyên giá chưa thuế {n0}, thuế đủ điều kiện khấu trừ {n1}. Chưa trả ncc_may.',
        'Máy có nguyên giá từ30 triệu đồng, thời gian sử dụng120 kỳ và đủ tiêu chuẩn TSCĐ. Ghi211; thuế khấu trừ của TSCĐ tách1332; công nợ riêng ncc_may.', party='ncc_may')
    add('loan', 'Nhận khoản vay ngân hàng', [('112','341',10_000_000)],
        'Hợp đồng vay và báo Có {n0}. Đây là vay, không phải vốn góp. Hồ sơ toàn bộ dư nợ đầu kỳ và khoản mới xác nhận phải trả trong12 tháng tới.', 'Tăng112 và nợ vay341; dòng tiền tài chính, dư nợ ngắn hạn trên B01.', 'financing')
    add('issue', 'Xuất nguyên liệu cho sản xuất', [('621','152',8_000_000)],
        'Phiếu xuất cho lệnh sản xuất SP01: trị giá xuất kho đã xác định {n0}.',
        'Tập hợp chi phí nguyên liệu trực tiếp ở 621, giảm 152. Chưa ghi ngay giá vốn hàng bán.')
    add('production_wage', 'Tính lương công nhân trực tiếp', [('622','334',4_000_000)],
        'Bảng lương đã duyệt xác nhận chi phí nhân công trực tiếp {n0}; chưa thanh toán.', 'Lương sản xuất ghi 622 và nghĩa vụ với người lao động ghi 334.')
    add('overhead', 'Chi phí dịch vụ tại phân xưởng', [('627','331',1_000_000)],
        'Bảng phân bổ dịch vụ phân xưởng xác nhận chi phí phải ghi {n0}; khoản này không có GTGT được khấu trừ. Chưa trả ncc_dv.',
        'Tập hợp chi phí sản xuất chung 627; ghi phải trả nhà cung cấp dịch vụ.', party='ncc_dv')
    add('admin_wage', 'Tính lương bộ phận quản lý', [('642','334',2_000_000)],
        'Bảng lương bộ phận quản lý đã duyệt {n0}, chưa trả.', 'Lương quản lý ghi 642, không đưa vào chi phí nhân công trực tiếp 622.')
    add('charges', 'Ghi các khoản trích theo bảng lương', [('622','3383',800_000),('642','3383',400_000)],
        'Bảng tính nghĩa vụ do bộ phận lương cung cấp: phần doanh nghiệp chịu của sản xuất {n0}, quản lý {n1}. Bài này dùng số đã được xác định, không xác định tỷ lệ pháp luật.',
        'Phần doanh nghiệp chịu phân bổ vào chi phí bộ phận tương ứng và khoản phải nộp 3383.')
    add('production_dep', 'Khấu hao máy sản xuất', [('627','214',production_dep)],
        'Bảng khấu hao: máy đầu năm500.000 đồng/kỳ, các máy mới dùng120 kỳ, đủ một kỳ ngay khi sẵn sàng sử dụng theo giả định thời điểm đầu kỳ; phân xưởng chịu tổng {n0}.',
        'Khấu hao phân xưởng gồm tài sản đầu kỳ và các máy đã mua ở kỳ trước/kỳ này, ghi627/214; không giảm nguyên giá211.', scaled=False)
    add('admin_dep', 'Khấu hao tài sản quản lý', [('642','214',300_000)],
        'Bảng khấu hao tài sản quản lý đầu năm: {n0} trong kỳ; không có tăng giảm tài sản quản lý.', 'Khấu hao quản lý ghi642/214; chi phí không bằng một khoản tiền đã chi trong kỳ.', scaled=False)
    add('production_cost', 'Kết chuyển chi phí sản xuất', [('154','621',amount(8_000_000)),('154','622',amount(4_800_000)),('154','627',production_overhead)],
        'Bảng tập hợp SP01: nguyên liệu {n0}, nhân công gồm khoản trích {n1}, sản xuất chung {n2}; không còn chi phí bỏ sót.',
        'Chuyển621,622,627 vào154 để tập hợp giá thành, gồm khấu hao toàn bộ máy đang dùng; không kết chuyển trực tiếp vào911.',scaled=False)
    add('finished', 'Nhập kho sản phẩm hoàn thành', [('155','154',production_total)],
        'SP01 hoàn thành toàn bộ, không có dở dang cuối kỳ; bảng tính giá thành và phiếu nhập xác nhận {n0}.',
        'Sản phẩm hoàn thành ghi155, giảm154; tổng giá thành khớp cả ba nhóm chi phí.',scaled=False)
    add('product_sale', 'Bán sản phẩm và ghi giá vốn', [('131','511',20_000_000),('131','3331',2_000_000),('632','155',12_000_000)],
        'Khach_cu nhận và chấp nhận sản phẩm. Doanh thu chưa thuế {n0}, thuế đầu ra theo hóa đơn {n1}, giá vốn theo phiếu xuất {n2}; chưa thu tiền.',
        'Ghi doanh thu và nghĩa vụ thuế theo chứng từ, đồng thời ghi giá vốn 632 và giảm sản phẩm 155.', party='khach_cu')
    add('goods_sale', 'Bán hàng hóa thu tiền mặt', [('111','511',3_000_000),('111','3331',300_000),('632','156',2_000_000)],
        'Khách nhận hàng và trả tiền mặt: doanh thu chưa thuế {n0}, thuế đầu ra {n1}; hàng xuất có giá vốn {n2}.',
        'Tiền thu bằng doanh thu cộng thuế; ghi riêng doanh thu, thuế và giá vốn.', 'operating')
    add('discount', 'Giảm giá cho lô sản phẩm đã bán', [('521','131',1_000_000),('3331','131',100_000)],
        'Hồ sơ giảm giá và chứng từ thuế điều chỉnh đã hoàn tất: giảm doanh thu {n0}, giảm thuế đầu ra {n1}, trừ nợ khach_cu. Không có hàng trả lại.',
        'Giảm doanh thu qua 521, giảm nghĩa vụ thuế theo chứng từ, giảm công nợ; không tự giả định có hàng nhập lại.', party='khach_cu')
    add('wage_pay', 'Thanh toán lương đã ghi nhận', [('334','112',6_000_000)],
        'Tệp chuyển khoản đã đối chiếu bảng lương, tổng {n0}; không có khấu trừ bổ sung trong bộ dữ liệu.',
        'Giảm nghĩa vụ 334 và tiền gửi 112; không ghi lại chi phí lương.', 'operating')
    add('charge_pay', 'Nộp khoản trích đã ghi nhận', [('3383','112',1_200_000)],
        'Báo Nợ xác nhận đã nộp {n0}, khớp bảng nghĩa vụ kỳ này.', 'Giảm 3383 và 112; không ghi chi phí lần hai.', 'operating')
    add('insurance', 'Chi phí bảo hiểm cho nhiều kỳ', [('242','112',2_400_000)],
        'Chi trả hợp đồng bảo hiểm phục vụ quản lý {n0}, hưởng lợi 12 kỳ; dịch vụ không có thuế đầu vào khấu trừ trong bộ dữ liệu.',
        'Ghi chi phí chờ phân bổ 242 vì nhiều kỳ hưởng lợi; không ghi hết vào chi phí kỳ hiện tại.', 'operating')
    add('allocation', 'Phân bổ các hợp đồng bảo hiểm đang hưởng lợi', [('642','242',allocation)],
        'Mỗi kỳ mua một hợp đồng bảo hiểm12 kỳ. Bảng phân bổ gồm hợp đồng hiện tại và tất cả hợp đồng chưa hết từ các kỳ trước, tổng kỳ này {n0}.',
        'Giảm242 và ghi642 cho toàn bộ hợp đồng đang hưởng lợi, không bỏ sót chi phí kỳ trước chuyển sang.',scaled=False)
    add('machine_pay', 'Thanh toán nhà cung cấp máy', [('331','112',39_600_000)],
        'Chuyển {n0} trả toàn bộ hóa đơn ncc_may đã nhập TSCĐ; không phải nhà cung cấp nguyên liệu.',
        'Giảm công nợ máy 331. Dòng tiền đầu tư vì mua TSCĐ, dù tài khoản đối ứng là 331.', 'investing','ncc_may')
    add('loan_pay', 'Trả gốc vay', [('341','112',4_000_000)],
        'Báo Nợ trả gốc vay {n0}; lãi tách riêng ở chứng từ khác.', 'Trả gốc giảm 341; không ghi chi phí tài chính. Dòng tiền tài chính.', 'financing')
    add('interest', 'Trả lãi vay phục vụ kinh doanh', [('635','112',300_000)],
        'Lãi vay kỳ này {n0}, đã trả; không liên quan tài sản đủ điều kiện vốn hóa.',
        'Lãi vay là chi phí tài chính 635; tiền chi lãi vay trình bày hoạt động kinh doanh theo phương pháp trực tiếp.', 'operating')
    add('term_deposit', 'Gửi tiền kỳ hạn sáu tháng', [('1281','112',10_000_000)],
        'Chuyển {n0} sang khoản tiền gửi kỳ hạn 6 tháng; không đủ điều kiện là tương đương tiền.',
        'Tiền gửi kỳ hạn ghi 1281, không giữ ở 112. Dòng tiền đầu tư; không đưa vào tiền và tương đương tiền.', 'investing')
    if period>6:
        principal=10_000_000*(10+(period-7)%3)//10
        add('term_maturity','Thu tiền gửi kỳ hạn đã đáo hạn',[('112','1281',principal*103//100)],
            'Khoản gửi đầu kỳ'+str(period-6)+' đủ6 tháng, hợp đồng3%/6 tháng. Gốc'+_n(principal)+' và lãi đã dự thu'+_n(principal*3//100)+'; ngân hàng trả tổng{n0}.',
            'Giảm1281 cho cả gốc và lãi đã dự thu, không ghi515 lần hai. Khi lập B03 tách thu gốc mã24 và thu lãi mã27.', 'investing',scaled=False)
    deposit_interest=sum(50_000*(10+(p-1)%3)//10 for p in range(max(1,period-5),period+1))
    add('term_interest_accrual','Dự thu lãi tiền gửi có kỳ hạn',[('1281','515',deposit_interest)],
        'Hợp đồng3% cho6 kỳ, nhận lãi khi đáo hạn. Bảng từng khoản tiền gửi đang còn hiệu lực xác nhận lãi kiếm được trong kỳ{n0}; chưa thu tiền.',
        'Theo hướng dẫnTK128, lãi nhận sau ghiNợ1281/Có515 từng kỳ; khi nhận chỉ giảm1281, không tạo doanh thu lần hai.',scaled=False)
    usd=100*factor//10; trade_rate=25_000+(period-1)*100; close_rate=26_000+(period-1)*100
    previous_usd=sum(100*(10+(p-1)%3)//10 for p in range(1,period))
    fx_gain=usd*(close_rate-trade_rate)+previous_usd*100
    add('fx_invoice', 'Doanh thu dịch vụ bằng ngoại tệ', [('131','511',usd*trade_rate)],
        f'Dịch vụ hoàn thành cho khach_fx: {usd}USD; tỷ giá giao dịch thực tế{trade_rate}VND/USD theo hồ sơ ngân hàng; giá trị ghi sổ {{n0}}. Chưa thu tiền, không có thuế đầu ra trong bảng nghĩa vụ đã cung cấp.',
        'Ghi131/511 theo tỷ giá giao dịch thực tế; theo dõi USD ở sổ chi tiết, số nguyên tệ không tăng khi đánh giá lại.', party='khach_fx',scaled=False)
    add('fx_revalue', 'Đánh giá lại toàn bộ phải thu ngoại tệ', [('131','515',fx_gain)],
        f'Tất cả hóa đơn khach_fx từ đầu năm chưa thanh toán, tổng{previous_usd+usd}USD. Tỷ giá mua bán chuyển khoản trung bình cuối kỳ của ngân hàng thường giao dịch{close_rate}VND/USD. Khoản cũ đã đánh giá ở tỷ giá{close_rate-100}cuối kỳ trước. Bảng xác nhận tăng giá trị VND {{n0}}.',
        'Đánh giá cả khoản cũ và khoản mới theo tỷ giá cuối kỳ đã xác định; tăng131/515 nhưng không thay đổi USD và không tạo dòng tiền.', party='khach_fx',scaled=False)
    reserve=amount(400_000)
    reserve_before=0 if period==1 else 400_000*(10+(period-2)%3)//10
    difference=reserve-reserve_before
    add('allowance', 'Điều chỉnh dự phòng khoản phải thu khó đòi',
        [('642','2293',difference)] if difference>0 else [('2293','642',-difference)],
        'Bảng ước tính: dự phòng cần có cuối kỳ'+_n(reserve)+', số đã lập'+_n(reserve_before)+'. '+('Bổ sung' if difference>0 else 'Hoàn nhập')+' chênh lệch{n0}; không xóa nợ.',
        'Chỉ ghi chênh lệch giữa mức dự phòng cần có và số đang có: bổ sung642/2293 hoặc hoàn nhập2293/642.',scaled=False)
    add('admin_cash', 'Chi phí quản lý bằng tiền mặt', [('642','111',500_000)],
        'Phiếu chi và hồ sơ công tác phí quản lý xác nhận {n0}, phân loại chi phí khác bằng tiền; không có thuế đầu vào khấu trừ trong dữ liệu.',
        'Ghi chi phí quản lý và giảm tiền mặt; dòng tiền hoạt động kinh doanh.', 'operating')
    add('service_advance', 'Thu tiền dịch vụ cho ba kỳ', [('112','3387',6_000_000)],
        'Thu {n0} cho hợp đồng dịch vụ ba kỳ; điều kiện phân bổ doanh thu theo tiến độ đã được xác định, không có thuế đầu ra trong bộ dữ liệu.',
        'Thu tiền chưa đồng nghĩa ghi nhận toàn bộ doanh thu; phần chờ phân bổ theo hợp đồng ghi 3387.', 'operating')
    add('service_revenue', 'Ghi doanh thu các hợp đồng dịch vụ đang thực hiện', [('3387','511',service_revenue)],
        'Mỗi hợp đồng thực hiện3 kỳ. Biên bản gồm hợp đồng mới và hợp đồng cũ còn thời gian thực hiện, tổng phần hoàn thành kỳ này{n0}.',
        'Ghi phần hoàn thành của toàn bộ hợp đồng đang thực hiện, giảm3387 và tăng511; không bỏ sót các kỳ còn lại của hợp đồng cũ.',scaled=False)
    add('tax_current', 'Ghi thuế TNDN hiện hành', [('8211','3334',1_000_000)],
        'Bộ phận thuế cung cấp bảng xác định nghĩa vụ hợp lệ: thuế TNDN hiện hành kỳ này {n0}. Không suy ra thuế suất từ TT99.',
        'Ghi chi phí thuế hiện hành 8211 và khoản phải nộp 3334; xác định nghĩa vụ thực hiện theo luật thuế.')
    add('tax_deferred', 'Ghi thuế TNDN hoãn lại phải trả', [('8212','347',100_000)],
        'Bảng chênh lệch tạm thời chịu thuế và mức thuế dự kiến đã soát xét xác nhận tăng nghĩa vụ hoãn lại {n0}.',
        'Ghi chi phí thuế hoãn lại 8212 và thuế hoãn lại phải trả 347; không trộn với khoản thuế hiện hành 3334.')
    add('selling', 'Chi phí bán hàng đã chi trả', [('641','112',600_000)],
        'Hồ sơ dịch vụ tiếp thị thuê ngoài phục vụ bán hàng và báo Nợ xác nhận {n0}; không có thuế đầu vào khấu trừ trong bộ dữ liệu.',
        'Ghi chi phí bán hàng 641; không đưa vào chi phí quản lý hay giá kho.', 'operating')
    retained='4211' if period==1 else '4212'
    add('dividend', 'Ghi nhận nghĩa vụ chia cổ tức', [(retained,'332',2_000_000)],
        'Nghị quyết và hồ sơ pháp lý xác nhận công ty đã không còn quyền từ chối chi trả cổ tức {n0}, đủ lợi nhuận được phân phối.',
        'Giảm lợi nhuận đủ điều kiện phân phối: tháng1 dùng4211 của năm trước, các tháng sau dùng4212 đã kết chuyển từ kỳ trước. Ghi nghĩa vụTK332; cổ tức không là chi phí.')
    add('dividend_pay', 'Trả cổ tức đã công bố', [('332','112',2_000_000)],
        'Ngân hàng xác nhận trả {n0}, khớp nghĩa vụ cổ tức đã ghi nhận.', 'Giảm 332 và 112; dòng tiền tài chính.', 'financing')
    tax_bal=_post(dict(_opening(period)[0]),rows)
    deductible=max(-tax_bal.get('3331',0),0); offset=[]
    for account in ('1331','1332'):
        used=min(max(tax_bal.get(account,0),0),deductible)
        if used:offset.append(('3331',account,used));deductible-=used
    add('vat_offset','Khấu trừ GTGT đầu vào với thuế đầu ra',offset,
        'Bảng xác nhận GTGT được khấu trừ cuối kỳ: thuế đầu ra sau điều chỉnh'+_n(max(-tax_bal.get('3331',0),0))+
        ', số đủ điều kiện1331 '+_n(tax_bal.get('1331',0))+' và1332 '+_n(tax_bal.get('1332',0))+
        '. Phân bổ khấu trừ theo bảng: dùng1331 trước, phần còn lại1332; không vượt thuế đầu ra. Thuế đầu vào chưa dùng chuyển kỳ sau.',
        'Cuối kỳ ghiNợ3331/Có133 theo bảng khấu trừ; giảm đồng thời đầu ra phải nộp và đầu vào đã sử dụng, phần đầu vào còn được khấu trừ giữ nguyên133. Không là một dòng tiền.',scaled=False)
    add('close_discount', 'Kết chuyển giảm trừ doanh thu', [('511','521',1_000_000)],
        'Bảng khóa sổ: tổng phát sinh giảm trừ bên Nợ521 là {n0}.', 'Kết chuyển 521 sang 511 trước khi kết chuyển doanh thu thuần vào 911.', closing=True)
    balances=_post({},rows)
    add('close_revenue', 'Kết chuyển doanh thu thuần và tài chính', [('511','911',-balances['511']),('515','911',-balances['515'])],
        'Bảng khóa sổ đã trừ521: doanh thu thuần {n0}; doanh thu tài chính {n1}.', 'Kết chuyển doanh thu thuần511 và doanh thu tài chính515 vào911.', closing=True,scaled=False)
    add('close_expense', 'Kết chuyển chi phí và thuế', [('911',a,balances[a]) for a in ('632','635','641','642','8211','8212')],
        'Bảng chi phí khóa sổ: giá vốn {n0}; tài chính {n1}; bán hàng {n2}; quản lý {n3}; thuế hiện hành {n4}; thuế hoãn lại {n5}.',
        'Kết chuyển các chi phí vào bên Nợ911; chi phí sản xuất đã qua154/155/632, không chuyển trực tiếp621-627.', closing=True,scaled=False)
    profit=-balances['511']-balances['515']-sum(balances[a] for a in ('632','635','641','642','8211','8212'))
    add('close_profit', 'Kết chuyển lợi nhuận sau thuế', [('911','4212',profit)],
        'Bảng xác định kết quả sau thuế: kỳ này lãi {n0}.', 'Lãi kết chuyển Nợ911/Có4212; sau khóa sổ911 và các tài khoản doanh thu, chi phí đều hết số dư.', closing=True,scaled=False)
    return rows


def _post(balances, rows, debts=None):
    for task in rows:
        for line in task['_key']:
            for acct, sign in ((line['debit'],1), (line['credit'],-1)):
                balances[acct] = balances.get(acct,0) + sign * line['amount']
                if debts is not None and acct in ('131','331'):
                    key = acct + '|' + task['party']
                    debts[key] = debts.get(key,0) + sign * line['amount']
    return balances


@lru_cache(maxsize=12)
def _opening(period):
    balances, debts = dict(OPENING), dict(OPEN_DEBTS)
    for p in range(1, period): _post(balances, _transactions(p), debts)
    return balances, debts


def ledger(book):
    balances = dict(_opening(book['period'])[0])
    return _post(balances, _transactions(book['period'])[:book['at']])


def _values(book, complete=False):
    opening, start_debts = _opening(book['period'])
    transactions = _transactions(book['period'])
    rows = transactions if complete else transactions[:book['at']]
    balances, debts = dict(opening), dict(start_debts)
    _post(balances, rows, debts)
    period_bal = _post({}, [t for t in rows if not t['closing']])
    value = lambda a: period_bal.get(a,0)
    revenue = -value('511') - value('521')
    cost = value('632')
    pretax = revenue - cost - value('635') - value('641') - value('642') - value('515')
    tax = value('8211') + value('8212')
    profit = pretax - tax
    flows = dict(operating=0, investing=0, financing=0)
    for task in rows:
        if task['activity']:
            for line in task['_key']:
                flows[task['activity']] += line['amount'] * ((line['debit'] in ('111','112')) - (line['credit'] in ('111','112')))
    customer_debit = sum(max(v,0) for k,v in debts.items() if k.startswith('131|'))
    customer_advance = sum(max(-v,0) for k,v in debts.items() if k.startswith('131|'))
    supplier_advance = sum(max(v,0) for k,v in debts.items() if k.startswith('331|'))
    supplier_credit = sum(max(-v,0) for k,v in debts.items() if k.startswith('331|'))
    assets = sum(balances.get(a,0) for a in ('111','112','1281','1331','1332','152','154','155','156','211','214','2293','242','243','621','622','627')) + customer_debit + supplier_advance
    liabilities = supplier_credit + customer_advance - sum(balances.get(a,0) for a in ('332','3331','3334','334','3383','3387','341','347'))
    unclosed = -sum(balances.get(a,0) for a in ('511','515','521','632','635','641','642','8211','8212','911'))
    equity = -sum(balances.get(a,0) for a in ('411','4211','4212')) + unclosed
    cash_start = opening.get('111',0) + opening.get('112',0)
    cash_end = balances.get('111',0) + balances.get('112',0)
    return dict(assets=assets, liabilities=liabilities, equity=equity, revenue=revenue, cost=cost,
                pretax=pretax, tax=tax, profit=profit, cash_start=cash_start, cash_end=cash_end,
                cash_net=sum(flows.values()), **flows,
                customer_debit=customer_debit, customer_advance=customer_advance,
                supplier_advance=supplier_advance, supplier_credit=supplier_credit)


def reports(book): return _values(book)


def tasks(book):
    rows = list(_transactions(book['period']))
    totals = _values(book, complete=True)
    for rid, title, keys in [
        ('position','B01-DN · Báo cáo tình hình tài chính', ('assets','liabilities','equity')),
        ('profit','B02-DN · Báo cáo kết quả hoạt động kinh doanh', ('revenue','cost','pretax','tax','profit')),
        ('cashflow','B03-DN · Báo cáo lưu chuyển tiền tệ trực tiếp', ('operating','investing','financing','cash_net','cash_start','cash_end')),
    ]:
        names = dict(assets='Tổng tài sản', liabilities='Nợ phải trả', equity='Vốn chủ sở hữu', revenue='Doanh thu thuần',
                     cost='Giá vốn', pretax='Lợi nhuận trước thuế', tax='Tổng chi phí thuế TNDN', profit='Lợi nhuận sau thuế',
                     operating='Lưu chuyển thuần kinh doanh', investing='Lưu chuyển thuần đầu tư', financing='Lưu chuyển thuần tài chính',
                     cash_net='Lưu chuyển tiền thuần', cash_start='Tiền đầu kỳ', cash_end='Tiền cuối kỳ')
        rows.append(dict(id=rid, report=rid, title=title, kind='fields', prompt='Lấy số từ sổ đã ghi, điền các chỉ tiêu bằng VND.',
                         fields=[dict(id=k,label=names[k]) for k in keys], _key={k:totals[k] for k in keys},
                         explain='Báo cáo lấy số từ cùng nhật ký. B01 tách số dư Nợ/Có chi tiết công nợ; B02 lấy phát sinh trước kết chuyển; B03 loại chuyển tiền nội bộ và nghiệp vụ không bằng tiền.',
                         docs=[dict(id=rid+'_source', title='Căn cứ lập báo cáo', lines=['Đối chiếu Sổ cái, sổ chi tiết công nợ và phân loại dòng tiền trong tab Sổ sách.'])],
                         references=[dict(label='Thông tư 99/2025/TT-BTC',url=SOURCE,locator='Phụ lục IV – '+title)]))
    rows.append(dict(id='notes', report='notes', title='B09-DN · Thuyết minh chính sách và số liệu', kind='choice',
                     prompt='Chọn thuyết minh phù hợp với hồ sơ doanh nghiệp và số đã ghi.',
                     options=[dict(id='consistent',label='VND; hoạt động liên tục; trình bày công nợ theo từng đối tượng; tiền gửi 6 tháng ở1281; bảng thuế và tỷ giá có căn cứ riêng.'),
                              dict(id='offset',label='Bù khoản khách trả trước với khách còn nợ để báo cáo gọn; coi tiền gửi 6 tháng là tiền.'),
                              dict(id='cash_only',label='Chỉ ghi nghiệp vụ đã thu hoặc chi tiền; bỏ dự phòng, khấu hao và thuế hoãn lại.')],
                     _key='consistent', explain='Thuyết minh phải khớp đơn vị tiền tệ, cơ sở lập, chính sách và số chi tiết trong bộ sổ, giải thích các khoản trọng yếu và các giả định.',
                     docs=[dict(id='notes_source',title='Hồ sơ chính sách',lines=['Doanh nghiệp sản xuất – thương mại; kỳ tháng thuộc năm2026; VND; hoạt động liên tục; kê khai thường xuyên. Giá trị xuất kho đã được bảng tính giá thành xác định; tiền gửi 6 tháng không là tương đương tiền. Các nghĩa vụ thuế và bảng tỷ giá có hồ sơ độc lập.'])],
                     references=[dict(label='Thông tư 99/2025/TT-BTC',url=SOURCE,locator='Phụ lục IV – B09-DN')]))
    return rows


def inspect(book, task_id):
    rows = tasks(book)
    _need(book['at'] < len(rows) and rows[book['at']]['id'] == task_id, 'Mở chứng từ của việc đang làm.')
    if task_id not in book['inspected']: book['inspected'].append(task_id)


def submit(book, task_id, answer):
    rows = tasks(book)
    _need(book['at'] < len(rows) and rows[book['at']]['id'] == task_id, 'Làm theo thứ tự hồ sơ; việc này đã ghi hoặc chưa tới.')
    task = rows[book['at']]
    _need(task_id in book['inspected'], 'Mở và đọc chứng từ trước khi ghi sổ.')
    _need(_shape(task,answer), 'Câu trả lời chưa đúng định dạng; kiểm tài khoản và số tiền.')
    if not _check(task,answer):
        book['mistakes'] += 1
        return dict(correct=False,message='Chưa khớp chứng từ. Kiểm đúng kỳ, đối tượng, giá chưa thuế/thuế và bên Nợ/Có; xem Sổ sách rồi thử lại.')
    book['answers'][task_id] = tree_copy(answer)
    book['at'] += 1
    return dict(correct=True,message=task['explain'],done=book['at']==len(rows))


def _check(task, answer):
    if task['kind'] == 'entry':
        task = dict(task, _key=[(l['debit'],l['credit'],l['amount']) for l in task['_key']])
    return procedures.check(task,answer)


def _shape(task, answer):
    # Annual enterprise totals exceed the small-career step engine's 1bn limit.
    if task['kind']=='fields':
        return isinstance(answer,dict) and set(answer)=={f['id'] for f in task['fields']} and all(type(v) is int and abs(v)<=10**15 for v in answer.values())
    if not procedures.shape_ok(task,answer):return False
    return task['kind']!='entry' or all(set(row)=={'debit','credit','amount'} for row in answer)


def next_period(book):
    _need(book['at'] == len(tasks(book)), 'Hoàn thành khóa sổ và bốn báo cáo trước khi mở kỳ tiếp.')
    _need(book['period'] < 12, 'Bạn đã hoàn thành trọn12 kỳ thực hành năm2026.')
    period = book['period'] + 1
    history=tree_copy(book['history'])
    history[str(book['period'])]=dict(answers=tree_copy(book['answers']),mistakes=book['mistakes'])
    book.update(initial(),period=period,history=history)


def public(book):
    from . import accounting_statements as statements
    rows = tasks(book)
    task = tree_copy(rows[book['at']]) if book['at'] < len(rows) else None
    if task:
        task.pop('_key');task.pop('explain')
        if task['id'] not in book['inspected']:
            task['docs'] = [dict(id=d['id'],title=d['title'],closed=True) for d in task['docs']]
    return dict(name=NAME, period=book['period'],year=2026,at=book['at'],total=len(rows),done=book['at']==len(rows),
                mistakes=book['mistakes'],paid=book['paid'],task=task,chart=dict(CHART),
                schedule=[dict(id=t['id'],title=t['title'],done=i<book['at'],current=i==book['at']) for i,t in enumerate(rows)],
                ledger=statements.trial_balance(book),details=statements.details(book),statements=statements.public(book),
                journal=[dict(id=t['id'],title=t['title'],entries=tree_copy(t['_key']),activity=t['activity']) for t in _transactions(book['period'])[:book['at']]],
                previous_journal=[dict(period=p,id=t['id'],title=t['title'],entries=tree_copy(t['_key']),activity=t['activity']) for p in range(1,book['period']) for t in _transactions(p)],
                reports=reports(book),references=[dict(label='Thông tư99 và phụ lục',url=SOURCE)],
                policy='Dữ liệu giả lập bằng VND; nghĩa vụ thuế, trích lương và giá trị quy đổi lấy từ bảng có sẵn. TT99 hướng dẫn ghi nhận và trình bày; không xác định nghĩa vụ thuế.')


def validate(book):
    from .engine import integer
    _need(isinstance(book,dict) and set(book)==set(initial()), 'Sổ doanh nghiệp không hợp lệ.')
    integer(book['period'],1,12)
    _need(isinstance(book['history'],dict) and set(book['history'])=={str(p) for p in range(1,book['period'])}, 'Thiếu bộ sổ đã hoàn thành của kỳ trước.')
    for period,proof in book['history'].items():
        prior=tasks(dict(period=int(period),at=0))
        _need(isinstance(proof,dict) and set(proof)=={'answers','mistakes'},'Hồ sơ khóa kỳ trước không hợp lệ.')
        integer(proof['mistakes'],0,10**6)
        _need(isinstance(proof['answers'],dict) and set(proof['answers'])=={t['id'] for t in prior},'Kỳ trước chưa đủ bút toán và báo cáo.')
        for t in prior:_need(_shape(t,proof['answers'][t['id']]) and _check(t,proof['answers'][t['id']]),'Bài thực hành kỳ trước không hợp lệ.')
    rows = tasks(book)
    integer(book['at'],0,len(rows));integer(book['mistakes'],0,10**6)
    _need(type(book['paid']) is bool and (not book['paid'] or book['at']==len(rows)), 'Kỳ lương chưa đủ điều kiện.')
    _need(isinstance(book['inspected'],list) and len(book['inspected'])<=len(rows) and all(type(x) is str for x in book['inspected']) and len(set(book['inspected']))==len(book['inspected']) and set(book['inspected'])<=set(t['id'] for t in rows), 'Danh sách chứng từ không hợp lệ.')
    _need(isinstance(book['answers'],dict) and set(book['answers'])==set(t['id'] for t in rows[:book['at']]), 'Tiến độ sổ không khớp đáp án.')
    for t in rows[:book['at']]:
        _need(t['id'] in book['inspected'] and _shape(t,book['answers'][t['id']]) and _check(t,book['answers'][t['id']]), 'Bút toán hoặc báo cáo đã lưu không hợp lệ.')
    _need(sum(ledger(book).values())==0, 'Sổ doanh nghiệp không cân đối Nợ/Có.')
    balances=ledger(book)
    _need(balances.get('111',0)>=0 and balances.get('112',0)>=0, 'Tiền mặt hoặc tiền gửi không kỳ hạn âm; đối chiếu chứng từ.')
