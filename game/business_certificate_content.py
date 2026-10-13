"""Business lessons use simplified game rules, not real-world legal advice."""


def _quiz(prefix, rows):
    questions = []
    for i, (text, right, wrong1, wrong2, why) in enumerate(rows):
        labels = [wrong1, wrong2]
        labels.insert(i % 3, right)
        questions.append(dict(id=f'{prefix}_{i + 1}', text=text,
                              options=[dict(id=k, label=v) for k, v in zip('abc', labels)],
                              answer='abc'[i % 3], why=why))
    return questions


GROUPS = [
    dict(
        id='business_basics', emoji='🛒', name='Chứng chỉ Kinh doanh cơ bản', short='Kinh doanh cơ bản',
        issuer='Trung tâm dạy nghề phường (lớp giả lập)', careers=(), hire=False, fee=500,
        allowed_modes=('class',), prerequisite=None, business_level=1,
        level_benefit='Mở nhiều xe đẩy và sạp; vẫn cần đủ tiền và đáp ứng điều kiện của quầy.',
        perk='Được mở nhiều xe đẩy và sạp. Chứng chỉ không tự cộng tiền hay tăng tỷ lệ xin việc.',
        intro='Học quản lý một quầy nhỏ: vốn, tồn kho, nhân viên và tiền thực còn lại. Quy tắc trong trò chơi.',
        notes=[
            'Vốn lưu động là tiền để quầy nhập hàng và trả chi phí. Đừng dùng hết tiền chỉ để mở quầy; xem quỹ và tiền bán hàng của từng quầy.',
            'Doanh thu là tiền bán được; lợi nhuận phải trừ giá vốn và các chi phí như lương, thuê chỗ, điện, thuế. Doanh thu cao chưa chắc có lãi.',
            'Quầy chỉ bán được hàng có trong kho. Xem tồn kho và đơn hàng đang về trước khi nhập; hàng chưa tới chưa thể bán.',
            'Nhân viên cần có ca làm và tiền lương. Thiếu hàng hoặc thiếu tiền có thể làm quầy dừng; thuê thêm người không thay thế việc nhập hàng.',
            'Tiền thuê chỗ, lương và thuế là chi phí cần theo dõi trong sổ quầy. Giữ một khoản dự phòng trước khi rút tiền về ví.',
            'Chứng chỉ cơ bản cho mở nhiều xe đẩy và sạp khi đủ điều kiện. Học phí gồm một lần thi; thi lại đóng nửa học phí hiện hành, làm tròn lên; không có thưởng tiền vì đỗ.',
        ],
        practice=_quiz('bb_p', [
            ('Mở quầy xong, vì sao cần để lại tiền?', 'Để nhập hàng và trả chi phí', 'Vì tiền để lại tự nhân đôi', 'Để khỏi phải xem kho', 'Quầy cần vốn lưu động để hoạt động.'),
            ('Bán được 100 xu có nghĩa là lãi 100 xu không?', 'Không, còn phải trừ chi phí', 'Có, doanh thu luôn là lãi', 'Có nếu có nhân viên', 'Doanh thu chưa trừ giá vốn, lương, thuê và thuế.'),
            ('Kho hết món bán chạy, nên xem gì?', 'Tồn kho và đơn nhập đang về', 'Màu giấy chứng nhận', 'Điểm phỏng vấn', 'Hàng trong đơn chưa giao chưa có sẵn để bán.'),
            ('Thuê thêm người có tự tạo ra hàng không?', 'Không, vẫn phải nhập hàng', 'Có, kho luôn đầy', 'Có nếu mở nhiều sạp', 'Nhân viên phục vụ khách; hàng bán vẫn lấy từ kho.'),
            ('Trước khi rút tiền quầy, nên làm gì?', 'Chừa tiền cho chi phí sắp tới', 'Rút hết vì quầy vẫn tự chạy', 'Chỉ nhìn số nhân viên', 'Quầy còn cần tiền lương, thuê và nhập hàng.'),
            ('Đỗ cơ bản giúp điều gì?', 'Mở nhiều xe đẩy và sạp khi đủ điều kiện', 'Tự có thêm tiền', 'Bỏ qua mọi học phí sau này', 'Chứng chỉ mở quyền kinh doanh, không cộng tiền.'),
        ]),
        bank=_quiz('bb_e', [
            ('Bạn đủ tiền mua xe đẩy nhưng không còn tiền nhập hàng. Nên làm gì?', 'Tích lũy thêm vốn vận hành', 'Mua ngay rồi chờ kho tự đầy', 'Thuê thật nhiều người', 'Tiền mở quầy và vốn vận hành đều cần thiết.'),
            ('Một quầy có tiền bán hàng và quỹ riêng. Khi quyết định nhập thêm, cần xem gì?', 'Tiền có thể dùng của chính quầy', 'Chỉ số chứng chỉ đã đỗ', 'Chỉ doanh thu của hôm trước', 'Vốn lưu động phải đủ tại quầy cần nhập hàng.'),
            ('Doanh thu 120 xu, tổng chi phí 90 xu. Còn lại bao nhiêu?', '30 xu', '120 xu', '210 xu', '120 trừ 90 bằng 30 xu.'),
            ('Hai quầy doanh thu bằng nhau nhưng một quầy thuê chỗ đắt hơn. Điều gì có thể xảy ra?', 'Quầy thuê đắt có lợi nhuận thấp hơn', 'Hai quầy luôn lãi bằng nhau', 'Tiền thuê không ảnh hưởng', 'Lợi nhuận chịu ảnh hưởng của chi phí thuê chỗ.'),
            ('Hàng mới đặt vẫn đang giao, kho hiện bằng 0. Có thể bán ngay hàng đó không?', 'Chưa, cần chờ hàng tới', 'Có, chỉ cần đã đặt', 'Có nếu có chứng chỉ', 'Quầy bán theo hàng thực có trong kho.'),
            ('Kho còn nhiều món bán chậm. Trước đơn nhập mới nên làm gì?', 'Xem lượng còn và nhu cầu rồi chọn số nhập', 'Nhập tối đa mọi món', 'Rút hết vốn', 'Kiểm tra tồn kho giúp tránh giam vốn vào hàng dư.'),
            ('Quầy có người làm nhưng không bán được vì hết hàng. Cách xử lý phù hợp?', 'Bổ sung hàng và kiểm tra hoạt động', 'Thuê thêm người để thay hàng', 'Thi lại chứng chỉ để sinh hàng', 'Nhân viên không thể bán hàng chưa có.'),
            ('Bạn thuê nhân viên mới. Khoản nào cần đưa vào dự trù?', 'Tiền lương', 'Thưởng tự động từ chứng chỉ', 'Tiền nhận việc của chính bạn', 'Nhân viên làm việc tạo ra chi phí lương của quầy.'),
            ('Sổ quầy ghi chi phí thuê và thuế. Có nên bỏ qua khi tính lãi?', 'Không, phải tính cùng các chi phí', 'Có vì đã có doanh thu', 'Có nếu làm xe đẩy', 'Thuê và thuế làm giảm tiền thực còn lại.'),
            ('Quỹ quầy sắp thiếu tiền trả chi phí. Nên ưu tiên gì?', 'Bổ sung vốn hoặc điều chỉnh hoạt động', 'Rút thêm tiền về ví', 'Mở quầy mới ngay', 'Giữ đủ vốn giúp quầy không ngừng vì thiếu tiền.'),
            ('Có chứng chỉ cơ bản, bạn muốn mở thêm một sạp. Cần gì nữa?', 'Đủ tiền và các điều kiện mở quầy', 'Không cần gì, mở miễn phí', 'Chỉ cần thi lại lấy 100 điểm', 'Chứng chỉ là điều kiện tiến triển, không thay thế tiền mở quầy.'),
            ('Sau khi đỗ, ví có tự tăng nhờ chứng chỉ kinh doanh không?', 'Không, quyền mở quầy là lợi ích', 'Có, nhận tiền thưởng vô hạn', 'Có, tự hoàn học phí', 'Chứng chỉ này không trao thưởng tiền hay hoàn học phí.'),
        ])),
    dict(
        id='business_advanced', emoji='🏪', name='Chứng chỉ Kinh doanh nâng cao', short='Kinh doanh nâng cao',
        issuer='Trung tâm dạy nghề phường (lớp giả lập)', careers=(), hire=False, fee=2000,
        allowed_modes=('class',), prerequisite='business_basics', business_level=2,
        level_benefit='Mở ki-ốt, tối đa 2 ki-ốt; vẫn cần đủ tiền và điều kiện của quầy.',
        perk='Được mở tối đa 2 ki-ốt. Không có thưởng tiền hoặc cộng cơ hội xin việc.',
        intro='Từ sạp lên ki-ốt: dự trù thuê chỗ, vốn nhập hàng và tổ chức nhân viên. Cần đỗ Kinh doanh cơ bản trước.',
        notes=[
            'Muốn học nâng cao phải có chứng chỉ cơ bản. Đỗ nâng cao mở quyền sở hữu tối đa 2 ki-ốt; phí mở và vốn quầy vẫn phải chuẩn bị riêng.',
            'Ki-ốt có chi phí vận hành: xem giá thuê, lương, điện và thuế trong quầy. Dự trù chi phí trước khi quyết định mở.',
            'Quản lý tồn kho theo tốc độ bán và hàng đang giao. Nhập quá nhiều giữ tiền trong kho; nhập quá ít dễ mất lượt bán vì hết hàng.',
            'Xem ca làm và chi phí từng nhân viên. Bổ sung người khi có nhu cầu và đủ vốn lương; nhiều người không bảo đảm nhiều khách.',
            'Theo dõi tiền quầy, doanh thu và các khoản chi riêng biệt. Trước khi rút lãi, chừa vốn nhập hàng cùng chi phí vận hành.',
            'Giá bán và thị trường tác động sức mua. Giá quá cao có thể giảm khách; so doanh thu với tổng chi phí, gồm tiền thuê và thuế, để điều chỉnh.',
        ],
        practice=_quiz('ba_p', [
            ('Điều kiện học nâng cao là gì?', 'Đã đỗ Kinh doanh cơ bản', 'Chỉ có tiền là đủ', 'Phải đỗ quản lý chuỗi trước', 'Các cấp học theo thứ tự cơ bản rồi nâng cao.'),
            ('Trước khi thuê ki-ốt cần dự trù khoản nào?', 'Thuê, nhân viên, nhập hàng và chi phí khác', 'Chỉ tiền trang trí', 'Chỉ học phí', 'Ki-ốt cần vốn hoạt động ngoài tiền mở.'),
            ('Nhập rất nhiều hàng bán chậm có rủi ro gì?', 'Tiền bị giữ trong tồn kho', 'Tự mất chứng chỉ', 'Thuế tự biến mất', 'Tiền đã mua hàng chưa quay về cho tới khi bán được.'),
            ('Khi nào nên cân nhắc thêm nhân viên?', 'Khi có nhu cầu phục vụ và đủ tiền lương', 'Bất cứ lúc nào để có khách vô hạn', 'Khi kho trống và không có vốn', 'Phải cân đối khả năng phục vụ với chi phí nhân viên.'),
            ('Tiền nào nên giữ ở quầy trước khi rút lãi?', 'Vốn nhập hàng và chi phí vận hành', 'Không cần giữ tiền', 'Chỉ tiền học khóa tiếp', 'Rút quá nhiều có thể làm quầy thiếu vốn.'),
            ('Tăng giá rất cao có luôn tăng lãi không?', 'Không, khách có thể mua ít hơn', 'Có, tăng giá là tăng lãi chắc chắn', 'Có nếu có hai ki-ốt', 'Sức mua thay đổi theo giá bán và thị trường.'),
        ]),
        bank=_quiz('ba_e', [
            ('Người chưa đỗ cơ bản muốn đóng tiền học nâng cao. Hệ thống xử lý thế nào?', 'Yêu cầu đỗ cơ bản trước, chưa thu học phí', 'Thu tiền rồi cấp bằng', 'Cho thi miễn phí', 'Điều kiện chứng chỉ được kiểm tra trước khi đóng phí.'),
            ('Bạn đã có hai ki-ốt và chứng chỉ nâng cao, muốn ki-ốt thứ ba. Cần học gì?', 'Quản lý chuỗi', 'Thi lại cơ bản là đủ', 'Không cần cấp tiếp theo', 'Nâng cao cho tối đa hai ki-ốt; ki-ốt thứ ba cần cấp quản lý chuỗi.'),
            ('Chi phí thuê tăng làm tiền còn lại thấp đi. Cần kiểm tra gì?', 'Khả năng trả chi phí và hiệu quả của ki-ốt', 'Chỉ điểm chứng chỉ', 'Chỉ số lần mở giao diện', 'Chi phí thuê ảnh hưởng vốn và lợi nhuận của ki-ốt.'),
            ('Có đủ phí mở ki-ốt nhưng chưa dự trù tiền lương. Kế hoạch còn thiếu gì?', 'Vốn vận hành', 'Điểm 100 tuyệt đối', 'Một chứng chỉ nghề bất kỳ', 'Lương là một phần vốn cần dự trù khi vận hành.'),
            ('Món bán nhanh sắp hết, đã có đơn giao sắp tới. Nên làm gì?', 'Xem lượng đang về rồi tính phần cần bổ sung', 'Bỏ qua đơn đang về và nhập tối đa', 'Ngừng xem tồn kho', 'Kết hợp tồn kho và hàng đang về tránh nhập trùng quá nhiều.'),
            ('Quầy còn nhiều món ít người mua trong khi thiếu tiền lương. Bài học nào phù hợp?', 'Cân đối vốn giữa tồn kho và chi phí', 'Cứ nhập thêm món đó', 'Chứng chỉ sẽ trả lương thay', 'Vốn bị giam trong kho có thể khiến chi phí khác thiếu tiền.'),
            ('Có nhiều người làm nhưng khách ít. Thêm người có chắc giải quyết được không?', 'Không, cần xem nhu cầu và chi phí', 'Có, mỗi người tự tạo khách', 'Có, lương không phải chi phí', 'Nhân sự cần tương xứng nhu cầu phục vụ.'),
            ('Một ca chưa có người làm. Khi sắp xếp cần xem gì?', 'Người phụ trách và khả năng trả lương', 'Chỉ màu biển hiệu', 'Số lần đã thi chứng chỉ', 'Ca làm cần người phù hợp và đủ ngân sách lương.'),
            ('Sổ ghi doanh thu tốt nhưng quỹ liên tục cạn. Nên xem tiếp gì?', 'Chi nhập hàng, lương, thuê, điện và thuế', 'Chỉ doanh thu', 'Chỉ tên ki-ốt', 'Cần xem dòng tiền ra cùng với doanh thu vào.'),
            ('Bạn định rút toàn bộ tiền hai ki-ốt. Cần cân nhắc điều gì?', 'Mỗi ki-ốt vẫn cần vốn nhập và trả chi phí', 'Có hai ki-ốt thì khỏi giữ vốn', 'Bằng nâng cao sẽ cấp vốn tự động', 'Từng ki-ốt phải duy trì vốn hoạt động.'),
            ('Tăng giá xong ít khách hơn. Cách xử lý phù hợp?', 'Xem giá và thị trường rồi điều chỉnh', 'Tiếp tục tăng vì lãi chắc cao hơn', 'Thi lại để loại bỏ ảnh hưởng giá', 'Giá và thị trường đều ảnh hưởng sức mua.'),
            ('Đánh giá ki-ốt nào hiệu quả hơn nên so gì?', 'Lợi nhuận sau tổng chi phí và vốn cần giữ', 'Chỉ ki-ốt nào doanh thu lớn hơn', 'Chỉ ki-ốt nào nhiều nhân viên hơn', 'Doanh thu lớn không chắc còn lại nhiều tiền sau chi phí.'),
        ])),
    dict(
        id='business_chain', emoji='🏬', name='Chứng chỉ Quản lý chuỗi', short='Quản lý chuỗi',
        issuer='Trung tâm dạy nghề phường (lớp giả lập)', careers=(), hire=False, fee=5000,
        allowed_modes=('class',), prerequisite='business_advanced', business_level=3,
        level_benefit='Mở ki-ốt thứ 3 trở đi; vẫn cần đủ tiền và điều kiện của từng quầy.',
        perk='Được mở ki-ốt thứ 3 trở đi. Chứng chỉ không tự tăng doanh thu hoặc tặng tiền.',
        intro='Giữ nhiều điểm bán hoạt động: theo dõi từng quầy, phân bổ vốn và mở rộng có dự trù. Cần đỗ Kinh doanh nâng cao.',
        notes=[
            'Quản lý chuỗi học sau chứng chỉ nâng cao; đỗ cho mở ki-ốt thứ 3 trở đi. Mỗi quầy mới vẫn cần phí mở, hàng và vốn hoạt động.',
            'Xem sổ từng quầy rồi tổng hợp cả chuỗi: doanh thu, giá vốn, lương, thuê, điện và thuế. Một quầy lỗ có thể bị che bởi quầy khác lãi.',
            'Theo dõi tồn kho và đơn giao ở từng điểm bán. Quầy này còn hàng không có nghĩa quầy khác có sẵn hàng; xử lý đúng quầy đang thiếu.',
            'Bố trí ca làm và dự trù lương tại từng quầy. Mở nhiều điểm nhưng thiếu người hoặc thiếu vốn sẽ khó duy trì phục vụ.',
            'Phân bổ vốn theo nhu cầu nhập hàng và chi phí của từng quầy. Chừa dự phòng cho giai đoạn ít khách, tránh rút sạch vốn để mở điểm mới.',
            'Chỉ mở rộng khi hiểu hiệu quả các quầy hiện có. Cả phố có thể cùng giảm khách vì thị trường; chứng chỉ không bảo đảm lãi và không thưởng tiền.',
        ],
        practice=_quiz('bc_p', [
            ('Muốn học quản lý chuỗi cần chứng chỉ nào?', 'Kinh doanh nâng cao', 'Chỉ An toàn lao động', 'Không cần chứng chỉ trước', 'Quản lý chuỗi là cấp sau nâng cao.'),
            ('Vì sao cần xem sổ riêng từng điểm?', 'Để biết điểm nào đang lỗ hoặc thiếu vốn', 'Vì tổng doanh thu luôn sai', 'Để tự nhận thưởng tiền', 'Tổng chuỗi có lãi vẫn có thể gồm quầy đang lỗ.'),
            ('Một sạp hết hàng, sạp khác còn nhiều. Nên kiểm tra gì?', 'Kho và đơn nhập của sạp hết hàng', 'Chỉ tổng số chứng chỉ', 'Chỉ kho sạp còn hàng', 'Hàng và hoạt động được theo dõi tại từng quầy.'),
            ('Mở thêm điểm cần chuẩn bị nhân sự ra sao?', 'Tính ca làm và tiền lương cho điểm đó', 'Dùng chứng chỉ thay mọi nhân viên', 'Không cần dự trù lương', 'Mỗi quầy cần tổ chức hoạt động riêng.'),
            ('Khi ít khách, khoản dự phòng giúp gì?', 'Duy trì chi phí cần thiết và vốn hàng', 'Bảo đảm lãi vô hạn', 'Xóa mọi khoản thuế', 'Dự phòng hỗ trợ hoạt động khi tiền bán vào chậm.'),
            ('Đỗ quản lý chuỗi có bảo đảm quầy luôn lãi không?', 'Không, vẫn phải quản lý hoạt động', 'Có, không thể lỗ nữa', 'Có, hệ thống tặng tiền mỗi ngày', 'Chứng chỉ mở quyền phát triển, không bảo đảm lợi nhuận.'),
        ]),
        bank=_quiz('bc_e', [
            ('Đã đỗ cơ bản nhưng chưa đỗ nâng cao. Có vào học quản lý chuỗi được không?', 'Chưa, cần đỗ nâng cao trước', 'Có nếu chọn tự học', 'Có nếu trả gấp đôi', 'Các cấp chứng chỉ học theo thứ tự.'),
            ('Đã có chứng chỉ quản lý chuỗi, mở ki-ốt thứ tư có mất phí mở không?', 'Có, vẫn cần đủ tiền và điều kiện', 'Không, mọi ki-ốt đều miễn phí', 'Không, học phí thay tiền mở', 'Học phí không thay phí mở và vốn của quầy.'),
            ('Tổng chuỗi có lãi nhưng một điểm lỗ liên tục. Nên làm gì?', 'Xem riêng chi phí và hoạt động của điểm lỗ', 'Bỏ qua vì tổng vẫn có lãi', 'Chỉ đổi tên chứng chỉ', 'Sổ từng quầy giúp phát hiện vấn đề bị tổng số che khuất.'),
            ('Tổng hợp tiền còn lại của chuỗi cần trừ khoản nào?', 'Giá vốn và chi phí của tất cả điểm bán', 'Chỉ giá vốn quầy đầu tiên', 'Không cần trừ tiền thuê và thuế', 'Chi phí toàn chuỗi bao gồm từng quầy.'),
            ('Ki-ốt A hết món trong khi B còn món đó. Điều gì đúng?', 'Cần xử lý kho của A để A bán lại', 'A tự coi kho B là kho mình', 'Chứng chỉ tự tạo hàng ở A', 'Tồn kho được quản lý theo từng quầy.'),
            ('Nhiều điểm cùng đặt hàng. Cần theo dõi đơn giao thế nào?', 'Theo từng quầy và lượng đang về', 'Chỉ đếm tổng đơn, bỏ qua nơi nhận', 'Coi mọi đơn là hàng đã tới', 'Đúng nơi nhận và trạng thái giao giúp tránh thiếu hoặc nhập trùng.'),
            ('Một điểm có ca trống, điểm khác đủ người. Nên ưu tiên gì?', 'Kiểm tra bố trí người và ngân sách điểm thiếu', 'Thuê thêm ở điểm đã đủ trước', 'Bỏ qua vì tổng người nhiều', 'Đủ người toàn chuỗi không có nghĩa từng quầy đều được bố trí đủ.'),
            ('Lương toàn chuỗi tăng sau khi mở rộng. Cần làm gì?', 'Cập nhật dự trù vốn và xem hiệu quả nhân sự', 'Bỏ lương khỏi sổ', 'Thi lại để được miễn lương', 'Mở rộng làm tăng nhu cầu quản lý chi phí nhân viên.'),
            ('Có tiền mở điểm mới nhưng các quầy cũ thiếu vốn nhập. Nên ưu tiên gì?', 'Ổn định vốn của quầy đang hoạt động', 'Rút sạch tiền để mở ngay', 'Chờ chứng chỉ phát vốn', 'Mở rộng không nên làm các quầy cũ ngừng hoạt động vì thiếu vốn.'),
            ('Hai quầy cùng thiếu tiền, nhu cầu nhập và chi phí khác nhau. Phân bổ thế nào?', 'Dựa trên nhu cầu và chi phí từng quầy', 'Chia đều bất kể tình trạng', 'Chỉ cấp cho quầy có tên dài nhất', 'Phân bổ vốn cần dựa trên tình hình vận hành cụ thể.'),
            ('Các điểm cùng ít khách dù chưa đổi giá. Cần xem yếu tố nào?', 'Tình hình thị trường chung của phố', 'Chỉ lỗi giấy chứng nhận', 'Chỉ số lượng bằng đã đỗ', 'Thị trường chung có thể tác động nhiều điểm cùng lúc.'),
            ('Trước khi mở tiếp chuỗi, thông tin nào hữu ích nhất?', 'Hiệu quả, vốn dự phòng và khả năng vận hành hiện tại', 'Chỉ tổng số quầy muốn sở hữu', 'Chỉ học phí đã đóng', 'Mở rộng bền vững cần hiểu hoạt động và vốn đang có.'),
        ])),
]
