"""Twenty-four foundation lessons, authored for this game."""
from .accounting_content import lesson as L, choice as C, number as N, entry as E, fields as F, order as O, multi as M, match as G, build_course


def build_basic():
    chapters = []
    chapters.append(('principles', '1. Bản chất và nguyên tắc kế toán', [
        L('entity', 'Đơn vị kế toán và người sử dụng thông tin', ['Tách tài sản của đơn vị khỏi tài sản cá nhân', 'Nhận diện quyết định cần thông tin kế toán'], [
            'Kế toán phản ánh nguồn lực và nghĩa vụ của một đơn vị xác định. Tiền chủ doanh nghiệp đưa vào công ty khác với tiền chủ tự chi cho gia đình. Chỉ giao dịch có bằng chứng về quyền, nghĩa vụ hoặc kết quả của đơn vị mới đi vào sổ của đơn vị; người giữ tiền không đương nhiên là người sở hữu tiền.',
            'Nhà quản lý dùng số liệu để điều hành, chủ sở hữu đánh giá hiệu quả, bên cho vay xem khả năng trả nợ. Thông tin cần trung thực, có thể kiểm tra và kịp thời. Khi chưa rõ bản chất giao dịch, hãy truy hợp đồng, chứng từ và người phê duyệt thay vì chọn tài khoản theo dòng tiền nhìn thấy.'],
          ['Chủ chuyển 40.000.000đ vào tài khoản công ty theo hồ sơ góp vốn: tài sản và vốn chủ cùng tăng 40.000.000đ.', 'Chủ dùng tài khoản cá nhân mua đồ gia đình 2.000.000đ: không ghi chi phí công ty.'], [
            C('Chủ mua vé nghỉ riêng bằng tiền cá nhân. Sổ công ty xử lý thế nào?', 'Không ghi vào sổ công ty', 'Ghi chi phí bán hàng', 'Ghi doanh thu', explain='Giao dịch không thuộc đơn vị kế toán.'),
            N('Chủ góp tiền 25.000.000đ rồi công ty vay 15.000.000đ. Tổng tiền công ty tăng bao nhiêu?', 40000000, 'Hai nguồn đều làm tiền tăng: 25.000.000 + 15.000.000 = 40.000.000đ.'),
            M('Người cho vay cần xem những thông tin nào để xét khả năng trả nợ?', ['Số tiền và thời hạn các khoản vay', 'Dòng tiền của doanh nghiệp'], ['Màu logo của chủ doanh nghiệp'], 'Nợ đến hạn và dòng tiền là thông tin trực tiếp về khả năng trả nợ.')],
          C('Công ty giữ 8.000.000đ tiền ký quỹ phải hoàn lại cho khách. Bản chất nguồn tiền là gì?', 'Nghĩa vụ phải trả của công ty', 'Doanh thu ngay khi thu tiền', 'Vốn cá nhân của thủ quỹ', explain='Quyền giữ tiền không xóa nghĩa vụ hoàn trả ký quỹ.'), 'Điều 1, 3; nguyên tắc Luật Kế toán'),
        L('equation', 'Phương trình kế toán', ['Tính tài sản, nợ phải trả và vốn chủ', 'Phân tích ảnh hưởng kép của giao dịch'], [
            'Phương trình tài sản = nợ phải trả + vốn chủ sở hữu mô tả nguồn hình thành tài sản. Tài sản là nguồn lực đơn vị kiểm soát; nợ là nghĩa vụ hiện tại phải thanh toán; vốn chủ là phần còn lại sau khi trừ nợ. Tiền vay làm tài sản tăng nhưng không tạo lợi nhuận hay vốn góp.',
            'Một giao dịch luôn giữ phương trình cân bằng khi ghi nhận đầy đủ. Mua hàng bằng tiền chỉ chuyển từ tiền sang hàng; mua chịu làm hàng và nợ cùng tăng. Trả nợ giảm tiền và giảm nợ. Lợi nhuận làm vốn chủ tăng, còn chủ rút vốn làm vốn chủ giảm theo hồ sơ hợp lệ.'],
          ['Tài sản 90.000.000đ, nợ 35.000.000đ: vốn chủ = 55.000.000đ.', 'Vay thêm 10.000.000đ: tài sản 100.000.000đ, nợ 45.000.000đ; vốn chủ vẫn 55.000.000đ.'], [
            N('Tài sản 76.000.000đ, nợ 21.000.000đ. Vốn chủ bao nhiêu?', 55000000, '76.000.000 − 21.000.000 = 55.000.000đ.'),
            F('Mua hàng chịu 6.000.000đ. Điền mức tăng của tài sản và nợ.', [('assets', 'Tài sản tăng', 6000000), ('liabilities', 'Nợ tăng', 6000000)], 'Hàng và nghĩa vụ trả người bán cùng tăng 6.000.000đ.'),
            C('Trả nợ người bán bằng tiền có làm phát sinh chi phí lần nữa không?', 'Không, chỉ giảm tiền và nợ đã ghi', 'Có, toàn bộ tiền trả là chi phí', 'Có, luôn ghi doanh thu âm', explain='Chi phí hoặc tài sản đã được ghi khi mua; thanh toán không ghi lặp.')],
          N('Một đơn vị có vốn chủ 62.000.000đ và nợ 18.000.000đ. Tổng tài sản phải bằng bao nhiêu?', 80000000, 'Theo phương trình: 62.000.000 + 18.000.000 = 80.000.000đ.'), 'Điều 3; Phụ lục IV – Báo cáo tình hình tài chính'),
        L('accrual', 'Cơ sở dồn tích và tính trọng yếu', ['Phân biệt ghi nhận với thu chi', 'Áp dụng xét đoán trọng yếu có chứng cứ'], [
            'Theo cơ sở dồn tích, nghiệp vụ được ghi khi phát sinh quyền, nghĩa vụ và thỏa điều kiện ghi nhận, không đợi tiền thu hoặc chi. Bán hàng chịu có thể tạo doanh thu và phải thu; chi phí điện dùng trong tháng có thể ghi nhận cùng nợ phải trả dù tháng sau mới nhận hoặc thanh toán hóa đơn.',
            'Tính trọng yếu xét khả năng thông tin thiếu hoặc sai ảnh hưởng quyết định của người sử dụng, cả về quy mô lẫn bản chất. Trọng yếu không cho phép bỏ qua chứng từ hay cố ý sai. Đơn vị phải áp dụng nhất quán chính sách phù hợp chuẩn mực và thuyết minh xét đoán đáng kể; TT99 không thay toàn bộ VAS.'],
          ['Dịch vụ hoàn thành tháng 3 giá 12.000.000đ, thu tiền tháng 4: ghi doanh thu và phải thu tháng 3 nếu đủ điều kiện.', 'Điện tháng 3 1.800.000đ có căn cứ ước tính đáng tin cậy: ghi chi phí tháng 3, sau đó đối chiếu hóa đơn.'], [
            C('Dịch vụ đã nghiệm thu, khách hẹn tháng sau trả. Khi nào xem xét ghi doanh thu?', 'Khi dịch vụ thỏa điều kiện ghi nhận', 'Chỉ khi có tiền mặt', 'Chỉ khi khóa sổ năm sau', explain='Dồn tích tách thời điểm ghi nhận khỏi thu tiền.'),
            N('Doanh thu đủ điều kiện tháng này 20.000.000đ; chi phí tương ứng 7.000.000đ. Lợi nhuận trước thuế bao nhiêu?', 13000000, '20.000.000 − 7.000.000 = 13.000.000đ, dù tiền chưa thu.'),
            C('Một khoản nhỏ có dấu hiệu gian lận. Có được bỏ qua vì số tiền nhỏ?', 'Không; bản chất cũng có thể trọng yếu', 'Được nếu dưới một triệu', 'Được nếu đã thu tiền', explain='Xét trọng yếu gồm cả bản chất và hoàn cảnh, không chỉ số tiền.')],
          C('Tiền khách ứng trước cho dịch vụ chưa thực hiện có luôn là doanh thu?', 'Không; cần xét nghĩa vụ và điều kiện ghi nhận', 'Có vì đã vào ngân hàng', 'Có vì có phiếu thu', explain='Thu tiền trước không tự chứng minh đã hoàn thành dịch vụ.'), 'Điều 3, 11; nguyên tắc VAS01 và VAS14'),
    ]))
    chapters.append(('records', '2. Chứng từ và kiểm soát', [
        L('voucher', 'Đọc và lập chứng từ kế toán', ['Xác định thông tin cần có', 'Truy dấu từ nghiệp vụ đến sổ'], [
            'Chứng từ ghi lại nghiệp vụ đã phát sinh và là căn cứ ghi sổ. Cần đọc ngày, số hiệu, bên giao nhận, nội dung, lượng, đơn giá, số tiền, người lập và chữ ký hoặc xác thực phù hợp. Chứng từ điện tử phải bảo đảm tính toàn vẹn và khả năng tra cứu; ảnh chụp mờ không đủ để suy diễn nội dung thiếu.',
            'Kiểm tra chứng từ trước khi hạch toán gồm kiểm tra hình thức, tính có thật và sự khớp giữa hợp đồng, giao nhận, hóa đơn, phê duyệt. TT99 có mẫu tham khảo nhưng đơn vị có thể thiết kế phù hợp yêu cầu pháp luật. Thay mẫu không đồng nghĩa miễn nội dung bắt buộc hay trách nhiệm kiểm soát.'],
          ['Mua 10 hộp × 300.000đ: tiền hàng 3.000.000đ; đối chiếu phiếu nhập xác nhận 10 hộp.', 'Nếu hóa đơn ghi 12 hộp nhưng kho nhận 10, lập hồ sơ xác minh trước khi ghi nhận phần chưa nhận.'], [
            N('Chứng từ mua 8 bộ × 450.000đ, chưa thuế. Tiền hàng bao nhiêu?', 3600000, '8 × 450.000 = 3.600.000đ.'),
            M('Chọn các đối chiếu cần thiết khi mua hàng.', ['Hóa đơn với hợp đồng', 'Số lượng hóa đơn với phiếu nhập'], ['Chỉ kiểm tra màu con dấu'], 'Phải kiểm tra cả điều khoản mua và thực nhận.'),
            O('Sắp xếp một quy trình ghi sổ sau khi nhận chứng từ.', ['Kiểm tra và phê duyệt chứng từ', 'Xác định tài khoản và kỳ ghi nhận', 'Ghi sổ và lưu liên kết chứng từ'], 'Chứng từ hợp lệ được phân tích trước khi đưa vào sổ.')],
          C('Phiếu nhập thiếu xác nhận người nhận. Hành động phù hợp là gì?', 'Bổ sung xác nhận đúng quy trình, không tự ký thay', 'Tự tạo chữ ký người nhận', 'Xóa chứng từ gốc', explain='Cần hoàn thiện căn cứ mà không làm giả hồ sơ.'), 'Điều 8–10; Phụ lục I'),
        L('control', 'Phân nhiệm và đối chiếu', ['Thiết kế kiểm soát tiền và hàng', 'Nhận diện xung đột nhiệm vụ'], [
            'Kiểm soát nội bộ giảm khả năng sai sót hoặc gian lận bằng phân nhiệm, phê duyệt, đối chiếu và giám sát. Người giữ tiền không nên đồng thời tự phê duyệt chi và tự đối chiếu sổ của mình. Đơn vị nhỏ có thể dùng kiểm soát bù trừ, như chủ xem sao kê độc lập và chứng từ gốc định kỳ.',
            'Đối chiếu là so hai nguồn độc lập và điều tra chênh lệch: sổ tiền với kiểm kê, sổ ngân hàng với sao kê, công nợ với xác nhận khách. Không ghi bút toán làm khớp cho đẹp khi chưa rõ nguyên nhân. Chênh lệch cần biên bản, người chịu trách nhiệm và xử lý được phê duyệt.'],
          ['Sổ quỹ 9.500.000đ, kiểm kê 9.300.000đ: thiếu 200.000đ; lập biên bản và xác minh.', 'Chủ đối chiếu sao kê trực tiếp từ ngân hàng với bảng chi do kế toán lập.'], [
            C('Ai nên đối chiếu tiền khi đã có thủ quỹ giữ tiền?', 'Người độc lập với việc giữ và chi tiền', 'Chỉ thủ quỹ tự xác nhận', 'Khách mua hàng bất kỳ', explain='Nguồn kiểm tra độc lập làm kiểm soát có hiệu lực.'),
            N('Sổ tồn 120 sản phẩm, kiểm kê 116, giá sổ 50.000đ mỗi sản phẩm. Giá trị thiếu là bao nhiêu?', 200000, '(120 − 116) × 50.000 = 200.000đ.'),
            C('Chênh lệch quỹ chưa rõ nguyên nhân nên làm gì?', 'Lập biên bản và xác minh, trình xử lý', 'Ghi giảm doanh thu tùy ý', 'Sửa sao kê ngân hàng', explain='Không thay bằng chứng hoặc tự chọn tài khoản để che chênh lệch.')],
          C('Một người vừa lập nhà cung cấp vừa duyệt chuyển tiền. Kiểm soát bổ sung nên ưu tiên?', 'Người khác duyệt nhà cung cấp và lệnh trả', 'Cho người đó tự kiểm tra cuối năm', 'Bỏ đối chiếu vì đã dùng phần mềm', explain='Tách quyền tạo đối tượng và phê duyệt thanh toán ngăn thanh toán giả.'), 'Điều 3; trách nhiệm tổ chức công tác kế toán'),
        L('audittrail', 'Sai sót, sửa sổ và lưu trữ', ['Giữ dấu vết sửa sai', 'Phân biệt sai kỳ hiện tại với sai kỳ trước'], [
            'Sổ kế toán phải lưu được nguồn số liệu và lịch sử xử lý. Khi sai tài khoản, số tiền hoặc kỳ ghi nhận, dùng phương pháp sửa sổ phù hợp, ghi rõ lý do và căn cứ. Xóa giao dịch đã khóa kỳ hoặc thay chứng từ gốc để mất dấu vết khiến người kiểm tra không thể tái lập số liệu.',
            'Sai sót phát hiện trong kỳ đang mở khác với sai trọng yếu của kỳ trước đã phát hành báo cáo. Sai kỳ trước cần đánh giá theo VAS29 và quy định liên quan về điều chỉnh hồi tố, trình bày lại và thuyết minh. Lưu trữ phải bảo đảm khả năng đọc, an toàn dữ liệu và thời hạn theo loại tài liệu, không coi sao lưu là thay thế mọi nghĩa vụ.'],
          ['Ghi chi phí 1.200.000đ thành 1.020.000đ trong kỳ mở: thiếu 180.000đ; lập điều chỉnh có tham chiếu chứng từ.', 'Hồ sơ lưu gồm bản gốc, bút toán điều chỉnh, phê duyệt và liên kết số chứng từ.'], [
            N('Một khoản 2.450.000đ đã ghi 2.150.000đ. Số cần điều chỉnh tăng là bao nhiêu?', 300000, '2.450.000 − 2.150.000 = 300.000đ.'),
            C('Sửa khoản đã khóa kỳ bằng cách xóa dấu vết có phù hợp không?', 'Không; cần điều chỉnh có căn cứ và lịch sử', 'Có nếu không ai hỏi', 'Có nếu số tiền nhỏ', explain='Dấu vết phục vụ đối chiếu và trách nhiệm giải trình.'),
            O('Sắp xếp việc xử lý sai sót vừa phát hiện.', ['Xác minh sai sót và kỳ bị ảnh hưởng', 'Phê duyệt phương án điều chỉnh', 'Ghi điều chỉnh và lưu hồ sơ'], 'Cần xác định bản chất và kỳ trước khi điều chỉnh.')],
          C('Sai trọng yếu năm trước đã phát hành báo cáo cần xét thêm chuẩn mực nào?', 'VAS29 về chính sách, ước tính và sai sót', 'Chỉ quy trình thu tiền', 'Chỉ bảng lương tháng hiện tại', explain='Cách sửa và thuyết minh sai kỳ trước phụ thuộc VAS29.'), 'Điều 12–13, 28, 30; VAS29'),
    ]))
    chapters.append(('doubleentry', '3. Tài khoản và ghi kép', [
        L('accounts', 'Nợ, Có và số dư', ['Xác định chiều tăng giảm', 'Đọc số dư tài khoản đúng bản chất'], [
            'Nợ và Có là tên hai bên tài khoản, không đồng nghĩa nợ tiền và có tiền trong đời thường. Tài sản thường tăng bên Nợ; nợ phải trả và vốn chủ thường tăng bên Có. Chi phí thường tăng bên Nợ và doanh thu thường tăng bên Có. Tài khoản điều chỉnh có chiều khác cần đọc hướng dẫn riêng.',
            'Số dư cuối kỳ bằng số dư đầu cộng tăng trừ giảm theo bản chất của tài khoản. Một tài khoản công nợ có thể có số dư chi tiết hai bên theo từng đối tượng; không bù trừ khách nợ với khách ứng trước. Tài khoản doanh thu, chi phí được kết chuyển nên thông thường không còn số dư sau khóa sổ.'],
          ['TK111 đầu kỳ dư Nợ 5.000.000đ, thu 3.000.000đ, chi 2.000.000đ: cuối kỳ dư Nợ 6.000.000đ.', 'TK331 dư Có 7.000.000đ, mua chịu thêm 4.000.000đ, trả 6.000.000đ: dư Có 5.000.000đ.'], [
            G('Ghép loại tài khoản với bên tăng thông thường.', [('Tài sản', 'Nợ'), ('Nợ phải trả', 'Có')], 'Tài sản và nguồn nợ có chiều tăng đối nhau.'),
            N('Tiền đầu kỳ 8.000.000đ, thu 5.000.000đ, chi 6.000.000đ. Tiền cuối kỳ?', 7000000, '8 + 5 − 6 = 7 triệu đồng.'),
            C('Dư Có chi tiết TK131 của một khách thường phản ánh gì?', 'Khách đã ứng trước', 'Tiền đang trong két', 'Chi phí khấu hao', explain='TK131 theo đối tượng có thể phản ánh ứng trước của khách.')],
          N('Nợ người bán đầu kỳ 9.000.000đ, mua chịu 5.000.000đ, trả 8.000.000đ. Nợ cuối kỳ?', 6000000, '9 + 5 − 8 = 6 triệu đồng.'), 'Điều 11; Phụ lục II – kết cấu tài khoản'),
        L('journal', 'Bút toán kép và định khoản', ['Ghi hai mặt của giao dịch', 'Kiểm tra tổng Nợ bằng tổng Có'], [
            'Định khoản bắt đầu từ bản chất nghiệp vụ: tài sản nào tăng giảm, nghĩa vụ nào phát sinh hoặc được thanh toán, doanh thu chi phí nào thỏa điều kiện. Sau đó chọn tài khoản và chiều Nợ Có. Mỗi bút toán có tổng Nợ bằng tổng Có; bút toán ghép có thể có nhiều tài khoản mỗi bên.',
            'Cân bút toán là điều kiện cần, chưa chứng minh ghi đúng: ghi Nợ tiền/Có doanh thu cho tiền vay vẫn cân nhưng sai. Trong trò chơi, mỗi dòng thể hiện một cặp Nợ/Có cùng số tiền; nhiều dòng có thể mô tả một chứng từ ghép. Luôn giữ giải thích và số chứng từ để kiểm tra bản chất.'],
          ['Mua hàng 4.000.000đ chưa thuế, chưa trả: Nợ156/Có331 4.000.000đ.', 'Trả nợ bằng tiền gửi 4.000.000đ: Nợ331/Có112 4.000.000đ; không ghi chi phí lần hai.'], [
            E('Mua hàng hóa 3.200.000đ, không xét thuế, nhập kho và chưa trả người bán.', [('156', '331', 3200000)], 'Hàng tăng bên Nợ156, nghĩa vụ tăng bên Có331.'),
            E('Thanh toán nợ người bán 2.700.000đ bằng tiền gửi không kỳ hạn.', [('331', '112', 2700000)], 'Nợ giảm Nợ331, tiền giảm Có112.'),
            C('Bút toán cân có chắc đúng bản chất không?', 'Không; cần kiểm tra tài khoản và chứng từ', 'Có vì tổng đã bằng nhau', 'Có nếu có hai dòng', explain='Ghi sai tài khoản có thể vẫn bảo toàn tổng Nợ/Có.')],
          E('Nhận vốn góp hợp lệ 18.000.000đ vào tài khoản thanh toán của công ty.', [('112', '411', 18000000)], 'Tăng tiền gửi và vốn đầu tư của chủ sở hữu.'), 'Điều 11; Phụ lục II – 112, 156, 331, 411'),
        L('ledger', 'Nhật ký, sổ cái và sổ chi tiết', ['Chuyển chứng từ thành dữ liệu sổ', 'Đối chiếu tổng hợp với chi tiết'], [
            'Nhật ký ghi nghiệp vụ theo thời gian; sổ cái tổng hợp theo từng tài khoản; sổ chi tiết theo khách, nhà cung cấp, vật tư, tài sản hoặc hợp đồng. Cùng một nghiệp vụ phải được liên kết giữa các sổ bằng số chứng từ và đối tượng, tránh nhập hai lần tạo giao dịch trùng.',
            'Tổng chi tiết phải đối chiếu với tài khoản tổng hợp theo cùng thời điểm và phạm vi. Sổ TK131 tổng hợp không đủ để đòi nợ nếu thiếu từng khách và hạn trả. Đơn vị có thể thiết kế sổ phù hợp nhưng phải cung cấp đủ thông tin để lập báo cáo và truy vết nghiệp vụ theo quy định.'],
          ['Khách An nợ 6.000.000đ, khách Bình nợ 4.000.000đ: tổng chi tiết phải thu 10.000.000đ.', 'Nếu sổ cái ghi 11.000.000đ, tìm chứng từ thiếu đối tượng hoặc bị ghi trùng 1.000.000đ.'], [
            N('Chi tiết ba khách dư Nợ 2.000.000đ, 3.500.000đ, 4.000.000đ. Tổng dư Nợ chi tiết?', 9500000, 'Cộng theo cùng bên: 2 + 3,5 + 4 = 9,5 triệu đồng.'),
            C('Sổ nào giúp biết hạn trả của từng khách?', 'Sổ chi tiết công nợ', 'Chỉ sổ tổng doanh thu', 'Chỉ bảng chấm công', explain='Chi tiết công nợ chứa đối tượng và điều kiện thanh toán.'),
            O('Sắp xếp dòng xử lý dữ liệu thông thường.', ['Chứng từ đã kiểm tra', 'Nhật ký và sổ chi tiết', 'Sổ cái và đối chiếu tổng hợp'], 'Dữ liệu có căn cứ được ghi rồi tổng hợp, đối chiếu.')],
          N('Sổ cái phải thu 16.000.000đ, tổng chi tiết 14.500.000đ. Chênh lệch cần điều tra?', 1500000, '16.000.000 − 14.500.000 = 1.500.000đ.'), 'Điều 12–13; Phụ lục III'),
    ]))
    chapters.append(('workingcapital', '4. Tiền, công nợ và hàng tồn kho', [
        L('cash', 'Tiền mặt và tiền gửi', ['Định khoản thu chi tiền', 'Đối chiếu số dư và phân loại tiền'], [
            'Tiền mặt tại quỹ theo dõi ở TK111; tiền gửi không kỳ hạn theo TK112. Tiền gửi có kỳ hạn được phân loại theo bản chất đầu tư, không mặc nhiên đưa hết vào112. Thu chi cần căn cứ, phê duyệt và thông tin người nhận; chuyển giữa quỹ và ngân hàng không tạo doanh thu chi phí.',
            'Sổ ngân hàng và sao kê có thể khác do thời điểm hạch toán, phí ngân hàng hoặc giao dịch chưa hoàn tất. Lập bảng đối chiếu từng nguyên nhân và chỉ ghi bổ sung khoản thuộc sổ đơn vị còn thiếu. Khoản thấu chi được phản ánh theo khoản vay, không trình bày112 âm như tiền hiện có.'],
          ['Rút 5.000.000đ từ tài khoản thanh toán về quỹ: Nợ111/Có112.', 'Ngân hàng trừ phí 20.000đ chưa ghi sổ: xác minh phí rồi ghi chi phí phù hợp/Có112.'], [
            E('Nộp tiền mặt 4.000.000đ vào tài khoản thanh toán, ngân hàng đã báo Có.', [('112', '111', 4000000)], 'Chỉ chuyển giữa hai loại tiền.'),
            N('Sổ tiền gửi 12.000.000đ, ngân hàng trừ phí chưa ghi 30.000đ. Số tiền sau bổ sung?', 11970000, '12.000.000 − 30.000 = 11.970.000đ.'),
            C('Theo TT99, TK112 có tên gì?', 'Tiền gửi không kỳ hạn', 'Mọi loại tiền gửi và tiền vay', 'Chi phí trả trước', explain='Tên TK112 được đổi phù hợp phạm vi tiền gửi không kỳ hạn.')],
          E('Rút tiền gửi không kỳ hạn về quỹ 7.500.000đ, đủ chứng từ.', [('111', '112', 7500000)], 'Tăng quỹ và giảm tiền gửi cùng số tiền.'), 'Phụ lục II – TK111,112,113,128,341'),
        L('receivable', 'Phải thu và phải trả', ['Phân biệt mua bán với thanh toán', 'Theo dõi từng đối tượng'], [
            'Bán hàng chưa thu tiền tạo phải thu khách hàng nếu đủ điều kiện ghi doanh thu. Mua hàng chưa trả tạo phải trả người bán. Khi thanh toán, giảm công nợ tương ứng thay vì ghi lại doanh thu hoặc giá mua. Cần theo từng khách, nhà cung cấp, hóa đơn, hạn thanh toán và ngoại tệ nếu có.',
            'Khoản ứng trước phải được phân loại theo đối tượng và bản chất. Khách ứng trước có thể là số dư Có chi tiết131; trả trước người bán là số dư Nợ chi tiết331. Không bù trừ tùy tiện giữa các bên vì làm mất thông tin về quyền thu và nghĩa vụ trả. Đối chiếu định kỳ giúp phát hiện thanh toán phân bổ sai.'],
          ['Bán chịu 9.000.000đ không xét thuế: Nợ131/Có511 9.000.000đ; giá vốn ghi riêng.', 'Khách trả 4.000.000đ: Nợ112/Có131; còn phải thu 5.000.000đ.'], [
            E('Khách thanh toán khoản nợ cũ 3.000.000đ bằng chuyển khoản.', [('112', '131', 3000000)], 'Thu nợ tăng tiền và giảm phải thu.'),
            N('Phải thu đầu tháng 8.000.000đ, bán chịu thêm 5.000.000đ, thu 7.000.000đ. Cuối tháng?', 6000000, '8 + 5 − 7 = 6 triệu đồng.'),
            C('Một khách trả trước chưa giao hàng. Có nên ghi doanh thu ngay chỉ vì đã thu tiền?', 'Không; theo dõi ứng trước và điều kiện doanh thu', 'Có, luôn ghi511', 'Có, ghi711', explain='Thu tiền và ghi doanh thu là hai quyết định riêng.')],
          N('Nợ người bán 13.000.000đ, trả 4.500.000đ, không mua thêm. Còn phải trả bao nhiêu?', 8500000, '13 − 4,5 = 8,5 triệu đồng.'), 'Phụ lục II – TK131,331'),
        L('inventory', 'Giá gốc và xuất kho', ['Tính giá tồn và giá xuất', 'Phân biệt hàng với chi phí kỳ'], [
            'Hàng tồn kho được ghi theo giá gốc phù hợp VAS02, gồm chi phí mua và chi phí cần thiết để đưa hàng về địa điểm, trạng thái hiện tại. Thuế được khấu trừ không đưa vào giá gốc; thuế không được hoàn lại có thể thuộc giá gốc. Chi phí bất thường và chi phí bán hàng không mặc nhiên vốn hóa vào kho.',
            'Chính sách tính giá xuất kho phải phù hợp và nhất quán, chẳng hạn bình quân hoặc nhập trước xuất trước. Theo dõi cả lượng và giá trị, đối chiếu kiểm kê và đánh giá giá trị thuần có thể thực hiện. Khi bán, ghi doanh thu riêng với giá vốn; tồn kho chưa bán không tự thành toàn bộ chi phí kỳ.'],
          ['10 sản phẩm giá 100.000đ và 10 sản phẩm giá 120.000đ: bình quân 110.000đ/sản phẩm.', 'Xuất 6 sản phẩm theo bình quân: giá vốn 660.000đ; còn 14 sản phẩm trị giá 1.540.000đ.'], [
            N('Tồn 5 sản phẩm giá 200.000đ; mua 5 sản phẩm giá 240.000đ. Đơn giá bình quân?', 220000, '(1.000.000 + 1.200.000)/10 = 220.000đ.'),
            E('Xuất hàng đã bán, giá vốn 1.400.000đ, theo kê khai thường xuyên.', [('632', '156', 1400000)], 'Giá vốn tăng và hàng hóa giảm.'),
            C('Phí vận chuyển hàng từ người bán về kho, cần thiết và bình thường thuộc đâu?', 'Giá gốc hàng mua', 'Vốn chủ sở hữu', 'Doanh thu tài chính', explain='Chi phí cần để đưa hàng về kho thuộc giá gốc theo điều kiện VAS02.')],
          N('Nhập trước 4 sản phẩm đơn giá 300.000đ, nhập sau 6 sản phẩm đơn giá 350.000đ. Xuất5 theo FIFO, giá xuất?', 1550000, '4 × 300.000 + 1 × 350.000 = 1.550.000đ.'), 'Phụ lục II – TK152,155,156,632; VAS02'),
    ]))
    chapters.append(('operations', '5. Tài sản dài hạn, doanh thu và chi phí', [
        L('fixedasset', 'Tài sản cố định và khấu hao', ['Tách giá mua với chi phí kỳ', 'Tính khấu hao đường thẳng'], [
            'Tài sản cố định dùng qua nhiều kỳ cần thỏa điều kiện ghi nhận theo chuẩn mực và quy định liên quan. Nguyên giá gồm khoản cần để đưa tài sản vào trạng thái sẵn sàng sử dụng, không chỉ giá hóa đơn. Chi phí vận hành hằng ngày và sửa chữa thông thường không tự trở thành nguyên giá.',
            'Khấu hao phân bổ giá trị phải khấu hao trong thời gian sử dụng hữu ích theo phương pháp phù hợp. Giá trị còn lại bằng nguyên giá trừ hao mòn lũy kế và các điều chỉnh liên quan. Khấu hao không phải lập quỹ tiền và không giảm tiền ngay; thời gian khấu hao kế toán và cách xác định chi phí thuế có thể khác nhau.'],
          ['Nguyên giá 60.000.000đ, giá trị thu hồi giả định 0, dùng5 năm: khấu hao năm12.000.000đ, tháng1.000.000đ.', 'Máy dùng quản lý: Nợ642/Có214 1.000.000đ mỗi tháng theo giả định.'], [
            N('Máy nguyên giá 48.000.000đ, giá trị thu hồi0, khấu hao đều48tháng. Khấu hao tháng?', 1000000, '48.000.000/48 = 1.000.000đ.'),
            E('Trích khấu hao máy phục vụ quản lý tháng này 800.000đ.', [('642', '214', 800000)], 'Chi phí quản lý tăng, hao mòn lũy kế tăng.'),
            C('Khấu hao có đồng nghĩa chi tiền mỗi tháng không?', 'Không; đây là phân bổ giá trị tài sản', 'Có; bắt buộc trả ngân hàng', 'Có; tiền tự chuyển sang quỹ', explain='Bút toán khấu hao không dùng tài khoản tiền.')],
          N('TSCĐ nguyên giá72.000.000đ, hao mòn lũy kế18.000.000đ. Giá trị còn lại?', 54000000, '72 − 18 =54 triệu đồng.'), 'Phụ lục II – TK211,213,214; VAS03,04'),
        L('revenue', 'Doanh thu và các khoản giảm trừ', ['Kiểm tra thời điểm doanh thu', 'Tính doanh thu thuần'], [
            'Doanh thu được ghi khi giao dịch thỏa điều kiện theo chuẩn mực, không đơn thuần khi xuất hóa đơn hoặc thu tiền. Với bán hàng cần xem việc chuyển giao, khả năng thu lợi ích và xác định giá trị; dịch vụ xem kết quả thực hiện phù hợp. Khoản thu hộ và thuế gián thu phải phân biệt với doanh thu của đơn vị.',
            'Doanh thu thuần phản ánh doanh thu sau các khoản giảm trừ phù hợp, như hàng trả lại, giảm giá và chiết khấu thương mại. Chiết khấu thanh toán vì trả sớm có bản chất tài chính khác chiết khấu thương mại. Giá vốn ghi riêng, không trừ trực tiếp vào tài khoản doanh thu để mất dấu vết.'],
          ['Bán hàng20.000.000đ, giảm giá hợp lệ1.000.000đ, không xét thuế: doanh thu thuần19.000.000đ.', 'Giá vốn12.000.000đ: lợi nhuận gộp7.000.000đ.'], [
            N('Doanh thu30.000.000đ, hàng trả lại2.000.000đ, giảm giá1.000.000đ. Doanh thu thuần?', 27000000, '30 −2 −1=27 triệu đồng.'),
            E('Dịch vụ đã hoàn thành đủ điều kiện, chưa thu tiền, giá chưa thuế4.000.000đ; đề không xét VAT.', [('131', '511', 4000000)], 'Ghi phải thu và doanh thu dịch vụ đã hoàn thành.'),
            C('Ưu đãi vì khách trả tiền sớm thuộc bản chất nào?', 'Chiết khấu thanh toán', 'Chiết khấu thương mại theo lượng', 'Vốn góp bổ sung', explain='Điều kiện thanh toán sớm tạo khoản tài chính.')],
          N('Doanh thu thuần45.000.000đ, giá vốn28.000.000đ. Lợi nhuận gộp?', 17000000, '45 −28=17 triệu đồng.'), 'Phụ lục II – TK511,521,632,635; VAS14'),
        L('expense', 'Chi phí và phân bổ nhiều kỳ', ['Phân loại chi phí theo chức năng', 'Phân bổ TK242 theo thời gian hưởng lợi'], [
            'Chi phí cần gắn với kỳ và chức năng sử dụng: bán hàng, quản lý, tài chính, sản xuất hoặc chi phí khác. Không chọn tài khoản theo người thanh toán. Một khoản dùng trong nhiều kỳ có thể ghi TK242 nếu thỏa điều kiện; theo TT99 tên là Chi phí chờ phân bổ và không chỉ giới hạn khoản đã trả bằng tiền.',
            'Phân bổ phải theo thời gian hoặc tiêu thức hưởng lợi hợp lý và có hồ sơ. Chi trước không luôn là chi phí chờ phân bổ: đặt cọc có thể là tài sản phải thu hoặc ký cược, mua máy có thể là TSCĐ. Ngược lại, khoản đủ điều kiện242 có thể đã phát sinh nghĩa vụ nhưng chưa thanh toán.'],
          ['Công cụ dùng quản lý trị giá6.000.000đ phân bổ6tháng: mỗi tháng1.000.000đ.', 'Ghi Nợ242/Có331 khi nhận đủ điều kiện chưa trả; mỗi tháng Nợ642/Có242 1.000.000đ.'], [
            N('Chi phí đủ điều kiện242 là9.000.000đ, phân bổ đều9tháng. Chi phí tháng?', 1000000, '9.000.000/9=1.000.000đ.'),
            E('Phân bổ chi phí chờ phân bổ dùng cho bán hàng tháng này500.000đ.', [('641', '242', 500000)], 'Tăng chi phí bán hàng và giảm giá trị chờ phân bổ.'),
            C('TK242 có chỉ ghi khi đã trả tiền không?', 'Không; xét chi phí thực tế và nhiều kỳ hưởng lợi', 'Có; cứ chi tiền đều242', 'Có; mọi khoản chưa trả đều331 và không có tài sản', explain='TK242 theo TT99 phản ánh chi phí thực tế chờ phân bổ cả đã trả và chưa trả.')],
          N('Khoản242 ban đầu12.000.000đ, đã phân bổ5tháng mỗi tháng1.000.000đ. Còn lại?', 7000000, '12 −5=7 triệu đồng.'), 'Phụ lục II – TK242,641,642'),
    ]))
    chapters.append(('adjustments', '6. Điều chỉnh và khóa sổ', [
        L('adjusting', 'Bút toán điều chỉnh cuối kỳ', ['Ghi đúng kỳ cho chi phí', 'Đối chiếu trước khóa sổ'], [
            'Cuối kỳ cần kiểm tra khoản chưa ghi, trả trước, phải trả, khấu hao, dự phòng và phân bổ. Bút toán điều chỉnh làm số liệu phản ánh tài sản, nghĩa vụ và kết quả đúng kỳ. Điều chỉnh phải có cơ sở ước tính hoặc chứng từ; không tạo chi phí tùy ý để đạt một mức lợi nhuận mong muốn.',
            'Phân biệt chi phí phải trả có căn cứ với dự phòng cho nghĩa vụ không chắc chắn. Khi có hóa đơn hoặc quyết toán thực tế, đối chiếu khoản ước tính và ghi chênh lệch đúng chính sách. Khóa sổ chỉ thực hiện sau đối chiếu tiền, hàng, công nợ và các sổ chi tiết quan trọng, với hồ sơ phê duyệt.'],
          ['Lãi vay đã phát sinh trong tháng600.000đ chưa trả: Nợ635/Có335 theo hồ sơ.', 'Khi chi trả600.000đ: Nợ335/Có112; không ghi lại chi phí lãi.'], [
            E('Lãi vay tháng này đã phát sinh700.000đ có căn cứ, chưa thanh toán và ghi chi phí phải trả.', [('635', '335', 700000)], 'Chi phí tài chính và chi phí phải trả cùng tăng.'),
            N('Chi phí điện đã ước tính1.800.000đ; thực tế2.000.000đ. Điều chỉnh tăng chi phí?', 200000, '2.000.000−1.800.000=200.000đ.'),
            C('Mục đích điều chỉnh cuối kỳ là gì?', 'Ghi tài sản, nghĩa vụ và kết quả đúng kỳ', 'Tự chọn lợi nhuận cho đẹp', 'Xóa mọi số dư nợ', explain='Điều chỉnh tuân theo bản chất và căn cứ của giao dịch.')],
          E('Phân bổ chi phí quản lý đã ghi242 kỳ này1.250.000đ.', [('642', '242', 1250000)], 'Đưa phần hưởng lợi kỳ này vào chi phí quản lý.'), 'Phụ lục II – TK242,335,352'),
        L('trialbalance', 'Bảng cân đối số phát sinh', ['Tính số dư theo phát sinh', 'Hiểu giới hạn kiểm tra cân đối'], [
            'Bảng cân đối số phát sinh tổng hợp số dư đầu, phát sinh Nợ Có và số dư cuối theo tài khoản. Tổng phát sinh Nợ phải bằng tổng phát sinh Có khi ghi kép đầy đủ. Tổng số dư theo hai bên cũng phải cân, nhưng đây là kiểm tra số học chứ không phải chứng nhận mọi giao dịch đúng.',
            'Giao dịch bỏ sót cả hai bên, ghi nhầm hai tài khoản hoặc ghi đúng số tiền nhưng sai kỳ vẫn có thể làm bảng cân. Cần kết hợp đối chiếu sổ chi tiết, chứng từ, kiểm kê và xét nội dung số dư bất thường. Không cộng doanh thu vào tiền để suy ra số dư quỹ vì chúng thuộc tài khoản khác.'],
          ['TK111 đầu10.000.000đ, phát sinh Nợ8.000.000đ, phát sinh Có6.000.000đ: dư cuối Nợ12.000.000đ.', 'Một giao dịch mua hàng chịu bị bỏ sót cả156 và331 không làm tổng Nợ/Có lệch.'], [
            N('TK112 dư đầu20.000.000đ, thu9.000.000đ, chi12.000.000đ. Dư cuối?', 17000000, '20+9−12=17 triệu đồng.'),
            C('Bỏ sót cả hai bên một giao dịch có thể làm bảng vẫn cân không?', 'Có', 'Không bao giờ', 'Chỉ khi số tiền bằng0', explain='Không có bên nào được ghi nên hai tổng vẫn có thể bằng nhau.'),
            F('Phát sinh Nợ toàn sổ85.000.000đ, phát sinh Có84.500.000đ. Điền tổng và lệch.', [('debit', 'Tổng Nợ', 85000000), ('difference', 'Chênh lệch', 500000)], 'Chênh500.000đ cần kiểm tra ghi kép và tổng hợp.')],
          N('TK331 dư Có11.000.000đ, phát sinh Có7.000.000đ và Nợ9.000.000đ. Dư Có cuối?', 9000000, '11+7−9=9 triệu đồng.'), 'Điều 12–13; Phụ lục III'),
        L('closing', 'Kết chuyển và xác định lợi nhuận', ['Kết chuyển doanh thu chi phí', 'Phân biệt tài khoản tạm thời và lâu dài'], [
            'Sau điều chỉnh, kết chuyển giảm trừ521 sang511 trước, rồi đưa doanh thu511,515,711 và chi phí632,635,641,642,811,821 phù hợp vào911. Chi phí sản xuất621,622,623,627 được xử lý qua tập hợp giá thành và154, không đưa toàn bộ thẳng vào911 bất kể sản phẩm đã bán hay chưa.',
            'Chênh lệch911 sau chi phí thuế được chuyển sang lợi nhuận sau thuế chưa phân phối năm nay. Lãi ghi Nợ911/Có4212; lỗ ghi ngược lại. Tài khoản tiền, tài sản, nợ và vốn không bị xóa cuối năm. Kết chuyển không tạo dòng tiền, và lợi nhuận giữ lại không có nghĩa toàn bộ nằm trong ngân hàng.'],
          ['Doanh thu thuần40.000.000đ, tổng chi phí32.000.000đ: lãi8.000.000đ theo giả định đã bao gồm thuế.', 'Kết chuyển lãi: Nợ911/Có4212 8.000.000đ.'], [
            E('Kết chuyển doanh thu511 sau giảm trừ là16.000.000đ sang911.', [('511', '911', 16000000)], 'Xóa doanh thu bên Nợ và ghi bên Có911.'),
            N('Doanh thu55.000.000đ, tổng chi phí sau thuế49.000.000đ. Lợi nhuận chuyển4212?', 6000000, '55−49=6 triệu đồng.'),
            C('TK112 có bị kết chuyển hết vào911 cuối năm không?', 'Không; số dư tiền được chuyển kỳ sau', 'Có, vì mọi tài khoản đều khóa về0', 'Có, chuyển vào doanh thu', explain='Tiền là tài khoản tài sản có số dư chuyển kỳ sau.')],
          E('Sau kết chuyển,911 xác định lỗ3.000.000đ kỳ hiện tại. Ghi sang4212.', [('4212', '911', 3000000)], 'Lỗ làm giảm lợi nhuận chưa phân phối.'), 'Phụ lục II – TK521,911,421'),
    ]))
    chapters.append(('reports', '7. Đọc bốn báo cáo tài chính', [
        L('position', 'Báo cáo tình hình tài chính', ['Phân loại nguồn lực và nghĩa vụ', 'Không bù trừ công nợ khác đối tượng'], [
            'Báo cáo tình hình tài chính trình bày tài sản, nợ phải trả và vốn chủ tại một thời điểm. Việc phân loại ngắn hạn, dài hạn dựa trên chu kỳ kinh doanh và điều kiện thời hạn theo quy định, không chỉ dựa tên tài khoản. Các tài khoản điều chỉnh giảm như hao mòn và dự phòng ảnh hưởng giá trị trình bày tài sản.',
            'Dư chi tiết Nợ131 và Có131 cần trình bày theo bản chất phải thu và người mua trả trước, không dùng số dư thuần của tài khoản để bù tất cả khách. Tương tự331 có trả trước người bán và phải trả. Đọc báo cáo cần xem thuyết minh kỳ hạn, tài sản thế chấp và nghĩa vụ để hiểu khả năng thanh toán.'],
          ['Khách A nợ6.000.000đ; khách B ứng trước2.000.000đ: trình bày phải thu6.000.000đ và nghĩa vụ2.000.000đ.', 'TSCĐ nguyên giá50.000.000đ trừ hao mòn10.000.000đ: giá trị còn lại40.000.000đ.'], [
            N('Tài sản150.000.000đ, nợ60.000.000đ. Vốn chủ trình bày?', 90000000, '150−60=90 triệu đồng.'),
            C('Khách khác nhau có dư Nợ và Có131. Có bù hết để trình bày một số không?', 'Không; phân loại theo chi tiết và bản chất', 'Có vì cùng131', 'Có vì cùng tháng', explain='Quyền thu và nghĩa vụ với các khách khác nhau cần trình bày đúng bản chất.'),
            F('Nguyên giá80.000.000đ, hao mòn25.000.000đ. Điền hai chỉ tiêu.', [('cost', 'Nguyên giá', 80000000), ('carrying', 'Giá trị còn lại', 55000000)], 'Giá trị còn lại80−25=55 triệu đồng.')],
          N('Hàng tồn kho giá gốc36.000.000đ và dự phòng giảm giá4.000.000đ. Giá trị trình bày thuần?', 32000000, '36−4=32 triệu đồng.'), 'Điều 17; Phụ lục IV – B01-DN'),
        L('performance', 'Báo cáo kết quả hoạt động kinh doanh', ['Tính lợi nhuận theo tầng', 'Phân biệt gộp, trước thuế và sau thuế'], [
            'Báo cáo kết quả hoạt động kinh doanh trình bày doanh thu, chi phí và kết quả của một kỳ. Doanh thu thuần trừ giá vốn ra lợi nhuận gộp; thêm kết quả tài chính và trừ chi phí bán hàng, quản lý tạo kết quả hoạt động. Thu nhập khác, chi phí khác và thuế tiếp tục ảnh hưởng lợi nhuận sau thuế.',
            'Lợi nhuận không bằng tổng thu tiền trừ tổng chi tiền: mua TSCĐ, vay vốn và trả nợ có thể làm tiền đổi mà không đi trực tiếp qua kết quả kỳ. Thuế thu nhập hiện hành và thuế thu nhập hoãn lại có căn cứ khác nhau. Đọc tỷ suất cần so cùng phạm vi, chính sách và kỳ để tránh kết luận sai.'],
          ['Doanh thu thuần100.000.000đ, giá vốn60.000.000đ: lợi nhuận gộp40.000.000đ.', 'Bán hàng10.000.000đ, quản lý12.000.000đ, không khoản khác: trước thuế18.000.000đ.'], [
            N('Doanh thu thuần80.000.000đ, giá vốn50.000.000đ. Lợi nhuận gộp?', 30000000, '80−50=30 triệu đồng.'),
            F('Lợi nhuận trước thuế20.000.000đ, chi phí thuế giả định4.000.000đ. Điền kết quả.', [('before_tax', 'Trước thuế', 20000000), ('after_tax', 'Sau thuế', 16000000)], 'Sau thuế20−4=16 triệu đồng.'),
            C('Khoản vay ngân hàng nhận trong kỳ có phải doanh thu kinh doanh không?', 'Không; phát sinh nghĩa vụ vay', 'Có; vì thu tiền', 'Có; ghi doanh thu tài chính toàn bộ', explain='Vay là giao dịch tài trợ vốn, không phải doanh thu.')],
          N('Lãi gộp25.000.000đ, lãi tài chính2.000.000đ, chi phí tài chính1.000.000đ, bán hàng4.000.000đ, quản lý7.000.000đ. Kết quả hoạt động?', 15000000, '25+2−1−4−7=15 triệu đồng.'), 'Điều 17; Phụ lục IV – B02-DN'),
        L('cashnotes', 'Lưu chuyển tiền tệ và thuyết minh', ['Phân loại ba dòng tiền', 'Đọc chính sách và thông tin bổ sung'], [
            'Báo cáo lưu chuyển tiền tệ chia dòng tiền thành hoạt động kinh doanh, đầu tư và tài chính. Thu từ khách và chi cho hoạt động thường thuộc kinh doanh; mua TSCĐ thuộc đầu tư; nhận vốn góp và vay thuộc tài chính. Chuyển giữa các khoản tiền hoặc tương đương tiền không tự tạo dòng lưu chuyển bên ngoài.',
            'Bản thuyết minh là thành phần của bộ báo cáo, trình bày chính sách kế toán, chi tiết chỉ tiêu, rủi ro và thông tin khác theo quy định. Báo cáo lợi nhuận và dòng tiền có thể khác do công nợ, tồn kho, khấu hao. Giao dịch không dùng tiền không ghi như dòng tiền nhưng có thể cần thuyết minh; phân loại chi tiết còn theo VAS24 và mẫu TT99.'],
          ['Thu khách30.000.000đ, chi hoạt động20.000.000đ: dòng kinh doanh10.000.000đ.', 'Mua máy8.000.000đ, nhận vốn5.000.000đ: tiền tăng ròng7.000.000đ nếu không khoản khác.'], [
            G('Ghép giao dịch với loại dòng tiền.', [('Thu nợ khách', 'Kinh doanh'), ('Mua máy sản xuất', 'Đầu tư'), ('Nhận vốn góp tiền', 'Tài chính')], 'Phân loại dựa bản chất hoạt động, không chỉ tài khoản ngân hàng.'),
            N('Tiền đầu kỳ9.000.000đ, dòng ròng kinh doanh6.000.000đ, đầu tư−4.000.000đ, tài chính3.000.000đ. Cuối kỳ?', 14000000, '9+6−4+3=14 triệu đồng.'),
            C('Chính sách khấu hao và phương pháp tính giá xuất kho được trình bày ở đâu?', 'Bản thuyết minh báo cáo tài chính', 'Chỉ phiếu thu', 'Chỉ giấy giao hàng', explain='Thuyết minh giúp người đọc hiểu cơ sở số liệu.')],
          C('Mua máy bằng khoản vay trả thẳng nhà cung cấp, không qua tiền doanh nghiệp, cần xử lý B03 thế nào?', 'Xem là giao dịch không dùng tiền và thuyết minh phù hợp', 'Ghi thu và chi tiền giả', 'Bỏ khỏi mọi thông tin báo cáo', explain='Không tạo dòng tiền không có thật; vẫn xem nghĩa vụ thuyết minh.'), 'Điều 17; Phụ lục IV – B03-DN,B09-DN; VAS24'),
    ]))
    chapters.append(('integrated', '8. Thuế, đạo đức và hồ sơ tổng hợp', [
        L('tax', 'Phân biệt kế toán với nghĩa vụ thuế', ['Tách lợi nhuận kế toán và thu nhập tính thuế', 'Dùng giả định thuế đúng phạm vi'], [
            'TT99 hướng dẫn chế độ kế toán; nghĩa vụ thuế được xác định bằng pháp luật thuế. Một khoản được ghi chi phí kế toán không có nghĩa chắc chắn được trừ khi tính thuế. Chênh lệch có thể vĩnh viễn hoặc tạm thời, cần hồ sơ đối chiếu; không sửa sai bản chất kế toán chỉ để làm bằng số trên tờ khai.',
            'Các bài học số học đặt tỷ lệ VAT, thuế thu nhập doanh nghiệp hoặc khấu trừ người lao động như giả định riêng của đề. Khi làm thực tế phải kiểm tra kỳ áp dụng, loại giao dịch, điều kiện chứng từ và văn bản thuế hiện hành. VAS17 cung cấp nguyên tắc thuế thu nhập hiện hành và hoãn lại, khác vai trò hệ thống tài khoản TT99.'],
          ['Lợi nhuận kế toán20.000.000đ có chi phí không được trừ2.000.000đ, giả định không chênh khác: thu nhập tính thuế22.000.000đ.', 'Thuế suất giả định20%: thuế hiện hành4.400.000đ; không suy từ ví dụ ra thuế suất cho mọi doanh nghiệp.'], [
            N('Lợi nhuận kế toán10.000.000đ, cộng chi phí không được trừ1.000.000đ, giả định không khoản khác. Thu nhập tính thuế?', 11000000, '10+1=11 triệu đồng theo giả định đề.'),
            N('Thu nhập tính thuế12.000.000đ, thuế suất đề giả định20%. Thuế hiện hành?', 2400000, '12.000.000×20%=2.400.000đ.'),
            C('TT99 có tự quyết định mọi thuế suất VAT không?', 'Không; phải dùng pháp luật thuế áp dụng', 'Có; mọi trường hợp đều cùng một tỷ lệ', 'Có; không cần xem hóa đơn', explain='Điều1 tách chế độ kế toán khỏi xác định nghĩa vụ thuế.')],
          N('Giá hàng10.000.000đ chưa thuế, VAT giả định10% và được khấu trừ. Tổng thanh toán?', 11000000, 'VAT1.000.000đ; tổng11.000.000đ.'), 'Điều 1; Phụ lục II – TK133,333,821; VAS17'),
        L('ethics', 'Đạo đức và xét đoán kế toán', ['Từ chối sửa chứng từ sai sự thật', 'Ghi rõ giả định và bằng chứng'], [
            'Người làm kế toán chịu trách nhiệm về số liệu và phải giữ tính trung thực. Áp lực tăng lợi nhuận không cho phép ghi doanh thu chưa đủ điều kiện, giấu nợ hoặc thay ngày chứng từ. Khi bất đồng, thu thập căn cứ, trao đổi người có thẩm quyền và lưu quyết định xử lý theo quy trình của đơn vị.',
            'Xét đoán hợp lý khác với đoán tùy ý: ước tính tuổi thọ tài sản cần dữ liệu sử dụng, dự phòng cần hồ sơ khả năng thu hồi, phân bổ cần tiêu thức hưởng lợi. Phân biệt điều đã biết, giả định và điều cần xác minh giúp người đọc đánh giá chất lượng thông tin. Bảo mật hồ sơ không có nghĩa che sai phạm với người có thẩm quyền kiểm tra.'],
          ['Bộ phận kinh doanh muốn ghi12.000.000đ đơn chưa giao: kiểm tra hợp đồng và điều kiện ghi nhận, không ghi vì chỉ tiêu.', 'Hồ sơ xét đoán tuổi thọ máy gồm hướng dẫn nhà sản xuất, tần suất dùng và quyết định phê duyệt.'], [
            C('Quản lý đề nghị đổi ngày chứng từ sang năm trước để tăng lãi. Cách xử lý?', 'Từ chối làm sai và trình căn cứ theo quy trình', 'Sửa ngày rồi xóa bản cũ', 'Ghi luôn vì cấp trên chịu hết trách nhiệm', explain='Chỉ đạo không thay thế trách nhiệm về tính trung thực.'),
            M('Ước tính kế toán đáng tin cậy cần gì?', ['Dữ liệu và căn cứ hợp lý', 'Phê duyệt và lưu hồ sơ xét đoán'], ['Chọn số để đạt lợi nhuận mong muốn'], 'Ước tính cần căn cứ và trách nhiệm giải trình.'),
            C('Chia sẻ sổ lương lên nhóm công khai để hỏi nghiệp vụ có phù hợp không?', 'Không; dùng dữ liệu đã ẩn danh và kênh có quyền', 'Có vì là số kế toán', 'Có nếu gửi ban đêm', explain='Thông tin nhân sự phải được bảo vệ theo quyền truy cập.')],
          C('Có hai phương án phân bổ chi phí. Nên chọn dựa trên tiêu chí nào?', 'Cách phản ánh hưởng lợi có căn cứ, áp dụng nhất quán', 'Cách làm lãi cao nhất', 'Cách có số tròn nhất', explain='Xét đoán phục vụ phản ánh trung thực, không phục vụ làm đẹp lãi.'), 'Điều 3,28; nguyên tắc Luật Kế toán'),
        L('cycle', 'Từ nghiệp vụ đến bộ báo cáo', ['Thực hiện chu trình đầy đủ', 'Kiểm tra mối liên hệ giữa báo cáo'], [
            'Chu trình kế toán bắt đầu từ chứng từ, định khoản, ghi nhật ký và sổ chi tiết, chuyển sổ cái, đối chiếu, điều chỉnh, kết chuyển rồi lập báo cáo. Mỗi bước có đầu vào và kiểm soát; bỏ kiểm kê hoặc công nợ có thể khiến số liệu cân nhưng thiếu thực tế. Bộ báo cáo TT99 gồm bốn thành phần liên hệ với nhau.',
            'Bài tổng hợp đơn giản vẫn phải phân biệt tiền, hàng, công nợ, doanh thu và lợi nhuận. Lãi chưa thu tiền làm phải thu tăng; mua hàng chưa bán làm kho tăng; vay làm tiền và nợ tăng. Tái lập từng số từ chứng từ giúp phát hiện sai. Chứng nhận hoàn thành trong trò chơi ghi nhận học tập, không thay chứng chỉ hành nghề ngoài đời.'],
          ['Nhận vốn20.000.000đ, mua hàng tiền mặt8.000.000đ, bán thu tiền12.000.000đ với giá vốn5.000.000đ, không thuế: tiền24.000.000đ, kho3.000.000đ.', 'Tài sản27.000.000đ = vốn góp20.000.000đ + lãi7.000.000đ; đối chiếu phương trình và kết quả.'], [
            N('Vốn tiền30.000.000đ; mua hàng10.000.000đ; bán thu tiền14.000.000đ. Tiền cuối kỳ?', 34000000, '30−10+14=34 triệu đồng.'),
            N('Hàng mua10.000.000đ, xuất bán giá vốn6.000.000đ. Tồn kho còn?', 4000000, '10−6=4 triệu đồng.'),
            O('Sắp xếp các bước cuối chu trình sau khi đã ghi sổ.', ['Đối chiếu và điều chỉnh', 'Kết chuyển kết quả', 'Lập và kiểm tra bộ báo cáo'], 'Số liệu được kiểm tra trước kết chuyển và báo cáo.')],
          F('Nhận vốn40.000.000đ; mua hàng12.000.000đ tiền; bán thu18.000.000đ, giá vốn8.000.000đ; không thuế và không khoản khác. Điền tiền, kho và lãi.', [('cash', 'Tiền', 46000000), ('stock', 'Kho', 4000000), ('profit', 'Lãi', 10000000)], 'Tiền40−12+18=46; kho12−8=4; lãi18−8=10 triệu. Tài sản50 bằng vốn40+lãi10.'), 'Điều 11–17; Phụ lục II–IV'),
    ]))
    return build_course('basic', 'Kế toán cơ bản',
                        '24 bài từ bản chất giao dịch, ghi kép và chứng từ đến khóa sổ và đọc đủ bốn thành phần báo cáo tài chính.', chapters)
