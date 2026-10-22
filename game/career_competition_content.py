"""Authored NPC-only leadership cases; no state, rewards, or career imports.

The bilingual pairs keep the English export next to its Vietnamese source.
Recognizers reuse established story characters when applicable. Competition peers
are explicitly fictional colleagues, distinct from customers and player accounts.
Rebuild the sidecar with ``python -m game.career_competition_content``.
"""

_EN = {}
PROFILES = {}


def _t(vi, en):
    _EN[vi] = en
    return vi


def _pair(value):
    return value.split(' // ', 1)


def _profile(cid, names, recognizer, focus, skills, assignment, allocation,
             inspection, correction, achievement, missing):
    """Build three complete cases from explicit, career-specific evidence."""
    rv, re = _pair(recognizer)
    fv, fe = _pair(focus)
    sv, se = (part.split(' | ') for part in _pair(skills))
    av, ae = _pair(assignment)
    gv, ge = _pair(allocation)
    iv, ie = _pair(inspection)
    cv, ce = _pair(correction)
    ev, ee = _pair(achievement)
    mv, me = _pair(missing)
    a, b, c = names.split(' | ')
    values = dict(a=a, b=b, c=c)
    gv, ge = gv.format(**values), ge.format(**values)
    rivals = [dict(id=f'{cid}_peer_{i + 1}', name=_t(name, name),
                   strength=_t(f'Đồng nghiệp NPC hư cấu · {v}', f'Fictional NPC colleague · {e}'))
              for i, (name, v, e) in enumerate(zip((a, b, c), sv, se))]
    cases = [
        ('assignment', 'Phân công trong ca', 'Assign the shift',
         f'{av} {a} vững {sv[0]}; {b} giỏi {sv[1]}; {c} chuyên {sv[2]}. Bạn phân công tổ NPC thế nào?',
         f'{ae} {a} is skilled in {se[0]}; {b} in {se[1]}; {c} in {se[2]}. How will you assign the NPC team?',
         [
             (gv, ge, 100,
              f'Phân công dùng đúng thế mạnh, có người kiểm lại trước bàn giao. Mục tiêu ca: {fv}.',
              f'The allocation uses each strength and includes a final check. Shift objective: {fe}.'),
             (f'Chia đều đầu việc cho {a}, {b}, {c}; ai xong tự bàn giao.',
              f'Divide tasks equally among {a}, {b}, and {c}; let each person hand over independently.', 50,
              f'Tổ có người phụ trách, nhưng chia đều chưa xét kỹ năng và thiếu kiểm tra chéo về {fv}.',
              f'Work has owners, but equal allocation ignores skills and lacks a cross-check for {fe}.'),
             (f'Giao toàn bộ cho {c} làm một mình để hai người còn lại nghỉ.',
              f'Ask {c} to handle everything alone so the other two can rest.', 0,
              f'Dồn việc cho một người bỏ qua thế mạnh của tổ; chưa bảo đảm {fv}.',
              f'Assigning everything to one person wastes team strengths and does not secure {fe}.'),
         ]),
        ('inspection', 'Kiểm tra trước bàn giao', 'Inspect before handover',
         f'{iv} {a} xin bạn nghiệm thu để kịp bàn giao. Bạn xử lý điểm chưa đạt thế nào?',
         f'{ie} {a} asks you to accept the work before the deadline. How will you handle the unresolved issue?',
         [
             (cv, ce, 100,
              f'Bạn yêu cầu sửa đúng điểm có bằng chứng và kiểm lại trước khi xác nhận: {fv}.',
              f'You require an evidence-based correction and verify it before acceptance: {fe}.'),
             (f'Nhờ {a} tự sửa điểm vừa phát hiện rồi bàn giao, không kiểm lại.',
              f'Ask {a} to fix the issue and hand over without a second check.', 50,
              f'Đã nhận ra sai sót nhưng chưa xác minh kết quả sửa. Hồ sơ nghiệm thu vẫn thiếu căn cứ về {fv}.',
              f'The issue is recognized, but the correction remains unverified. Acceptance still lacks evidence for {fe}.'),
             ('Xác nhận đạt ngay cho kịp giờ, ghi chú sửa ở ca sau.',
              'Accept the work now to meet the deadline and note a fix for the next shift.', 0,
              f'Ghi đạt khi sai sót còn tồn tại làm mất giá trị nghiệm thu; ca sau không thay thế việc kiểm {fv}.',
              f'Accepting unresolved work defeats inspection; the next shift cannot replace checking {fe} now.'),
         ]),
        ('commendation', 'Đề nghị ghi nhận đúng người', 'Recommend evidence-based recognition',
         f'Hồ sơ kỳ này: {a} {ev}. {b} làm nhiều lượt hơn nhưng thiếu {mv}. {c} hỗ trợ đều, chưa có hồ sơ kết quả riêng. Bạn gửi đề nghị nào tới {rv}?',
         f'This period: {a} {ee}. {b} handled more jobs but lacks {me}. {c} helped consistently but has no individual outcome record yet. What will you recommend to {re}?',
         [
             (f'Đề nghị ghi nhận {a}, đính kèm kết quả đã kiểm; giúp {b} và {c} hoàn thiện hồ sơ.',
              f'Recommend {a} with verified results; help {b} and {c} complete their evidence.', 100,
              f'Ghi nhận dựa trên hồ sơ: {a} {ev}. Đồng nghiệp cũng được hướng dẫn cải thiện. Đây là đề nghị trong tổ NPC, không tự cấp chức vụ.',
              f'Recognition follows the evidence: {a} {ee}. Colleagues also receive guidance. This NPC-team recommendation does not grant a job rank.'),
             ('Gửi lời cảm ơn cả tổ, hoãn đề nghị dù hồ sơ tốt đã được kiểm.',
              'Thank the entire team and postpone the recommendation despite the verified record.', 50,
              f'Lời cảm ơn hỗ trợ tinh thần, nhưng chưa ghi nhận đúng đóng góp đã kiểm của {a}.',
              f'Thanking the team supports morale, but does not recognize {a}\'s verified contribution.'),
             (f'Chọn {b} vì số lượt cao nhất, không cần bổ sung hồ sơ.',
              f'Choose {b} for the highest job count without requesting the missing records.', 0,
              f'Số lượt không bù được việc thiếu {mv}; đề nghị chưa có bằng chứng đạt chuẩn.',
              f'Job count does not make up for missing {me}; the recommendation lacks evidence of meeting the standard.'),
         ]),
    ]
    scenarios = []
    for index, (kind, tv, te, textv, texte, options) in enumerate(cases):
        # Stable varied positions: no universal "first answer is best" shortcut.
        rotate = (sum(map(ord, cid)) + index) % 3
        options = options[rotate:] + options[:rotate]
        scenarios.append(dict(id=f'{cid}_{kind}', title=_t(tv, te), text=_t(textv, texte),
                              options=[dict(id=oid, label=_t(v, e), score=score, feedback=_t(fbv, fbe))
                                       for oid, (v, e, score, fbv, fbe) in zip('abc', options)]))
    PROFILES[cid] = dict(recognizer=_t(rv, re), focus=_t(fv, fe), rivals=rivals, scenarios=scenarios)


_profile('garbage', 'Minh An | Bảo Bình | Ngọc Chi',
    'Chị Hạnh · tổ trưởng thu gom // Hạnh · waste collection team leader',
    'đủ tuyến, phân loại đúng và xử lý rác nguy hại an toàn // complete routes, correct sorting, and safe hazardous-waste handling',
    'phân loại rác | trao đổi với hộ dân | sắp xếp tuyến // waste sorting | communication with households | route planning',
    'Ngõ 12 có rác tái chế lẫn vật sắc nhọn; ngõ 14 phản ánh thường bị bỏ sót cuối tuyến. // Alley 12 has recyclables mixed with sharps; residents in Alley 14 report missed collections at the end of the route.',
    'Giao {a} rà phân loại an toàn, {b} xác minh phản ánh, {c} chia tuyến và đối chiếu điểm cuối cùng bạn. // Ask {a} to review safe sorting, {b} to verify the complaints, and {c} to allocate routes and check the final stop with you.',
    'Bảng tuyến đã đánh dấu đủ nhưng ảnh cuối ngõ 14 vẫn còn hai túi rác; ảnh không rõ loại rác. // The route sheet is complete, but a photo at the end of Alley 14 still shows two bags of unidentified waste.',
    'Xác minh thời điểm ảnh, kiểm điểm bỏ sót và phân loại trước khi bố trí thu gom lại; nghiệm thu có bằng chứng. // Verify the photo time, inspect the missed stop, classify the waste, arrange recollection, and verify completion.',
    'đã hoàn tất tuyến ngõ 14, có ảnh đối chiếu và xác nhận xử lý vật sắc nhọn đúng quy trình // completed Alley 14 with comparison photos and verified safe handling of sharps',
    'xác nhận điểm cuối tuyến và phân loại vật nguy hại // final-stop confirmation and hazardous-waste classification')

_profile('art_studio', 'Hà My | Quốc Bảo | Diệu Linh',
    'Chủ xưởng · hội đồng nghệ thuật // Studio owner · arts panel',
    'đúng đề bài, tôn trọng quyền tác giả và bàn giao tác phẩm hoàn chỉnh // meeting the brief, respecting authorship, and delivering finished artwork',
    'bố cục | phối màu | đóng khung và bàn giao // composition | color work | framing and delivery',
    'Khách đặt bộ ba tranh cùng câu chuyện, cần xem bản phác trước khi lên màu; thợ mới muốn vẽ ngay. // A client ordered three connected paintings and needs to approve sketches before coloring; a new artist wants to begin painting immediately.',
    'Giao {a} thống nhất phác thảo với khách, {b} thử bảng màu, {c} kiểm kích thước khung; duyệt mẫu chung rồi mới vẽ. // Have {a} confirm sketches with the client, {b} test the palette, and {c} check frame sizes; approve the set before painting.',
    'Tranh đúng màu nhưng chi tiết chính lấy nguyên hình của người khác, chưa có phép; phiếu bàn giao chưa ghi nguồn. // The colors match, but a central detail copies someone else\'s image without permission and the delivery sheet has no source attribution.',
    'Dừng bàn giao, làm rõ quyền sử dụng hoặc thay bằng sáng tác phù hợp; kiểm lại đề bài và nguồn trước nghiệm thu. // Hold delivery, resolve usage rights or replace the detail with suitable original work, then verify the brief and attribution.',
    'đã sửa bố cục theo bản phác được duyệt, ghi rõ nguồn tham khảo và bàn giao tranh đúng hẹn // revised the composition to the approved sketch, documented references, and delivered on time',
    'phê duyệt bản phác và xác minh quyền sử dụng hình // sketch approval and image usage verification')

_profile('laundry', 'Thùy Dung | Hoàng Nam | Yến Nhi',
    'Chủ tiệm · quản lý xưởng giặt // Shop owner · laundry supervisor',
    'đúng nhãn chăm sóc, không lẫn đồ và giao đúng khách // following care labels, keeping items separate, and returning them to the right customer',
    'đọc nhãn vải | xử lý vết bẩn | đối soát mã túi // reading fabric labels | stain assessment | bag-code reconciliation',
    'Đơn khách sạn có khăn trắng và một túi đồ lụa gửi riêng; giờ nhận trả trùng nhau. // A hotel order includes white towels and a separate bag of silk garments; pickup and return times overlap.',
    'Giao {a} tách lụa theo nhãn, {b} đánh giá vết bẩn từng nhóm, {c} giữ mã túi và cùng kiểm trước giao. // Ask {a} to separate silk by care label, {b} to assess stains by group, and {c} to maintain bag codes and join the handover check.',
    'Hai áo giống màu được treo cùng móc nhưng mã nhận khác khách; một nhãn chăm sóc chưa được đối chiếu. // Two shirts of the same color share a hanger despite belonging to different customers; one care label has not been checked.',
    'Tạm giữ hai áo, đối chiếu mã nhận và nhãn chăm sóc, sửa phiếu rồi kiểm cùng người đóng gói trước trả. // Hold both shirts, reconcile intake codes and care labels, correct the sheet, and verify with the packer before return.',
    'đã tìm đúng chủ túi đồ lụa bằng mã nhận và kiểm đủ món với khách // matched the silk bag to its owner using the intake code and confirmed every item with the customer',
    'đối chiếu mã nhận và tình trạng vải trước trả // intake-code reconciliation and fabric-condition checks before return')

_profile('restore', 'Minh Khoa | Bảo Ngọc | Quốc Thắng',
    'Hội nghề phục chế · chủ xưởng Hồn Xưa // Restorers guild · Hồn Xưa workshop owner',
    'giữ hồn đồ xưa, ghi đúng tuổi đồ và nói thật với khách // keeping old pieces true, recording their real age, and being honest with customers',
    'đọc dấu hiệu hư hỏng | chốt yêu cầu khách | ghi nguồn linh kiện // reading damage signs | settling customer requests | recording part sources',
    'Một tủ thờ gỗ gụ có mọt và bong sơn, khách muốn giữ mùi long não nhưng bên trong có mốc. // A rosewood altar cabinet has woodworm and flaking paint; the customer wants to keep its camphor smell, but there is mould inside.',
    'Giao {a} khám dấu hiệu từng chỗ hư, {b} chốt yêu cầu với khách có ghi phiếu, {c} lo linh kiện và ảnh trước sau. // Have {a} examine each damaged spot, {b} settle the request with the customer in writing, and {c} handle parts and before-and-after photos.',
    'Một tay nắm đồng bị thay bằng đồ nhựa mà phiếu không ghi; tuổi đồ trên phiếu theo lời khách, không theo tem đáy. // A brass handle was replaced with plastic without a note on the ticket, and the age on the ticket follows the customer, not the maker stamp.',
    'Dừng bàn giao, chế lại tay nắm cùng vật liệu, sửa tuổi đồ theo tem và báo khách trước khi trả. // Hold the handover, remake the handle in the same material, correct the age from the stamp, and tell the customer before returning it.',
    'đã giữ nguyên mùi gỗ cũ, lau mốc từng chỗ và giao tủ kèm biên bản phục chế có ảnh // kept the old wood smell, cleaned the mould spot by spot, and handed back the cabinet with an illustrated restoration report',
    'đối chiếu tuổi đồ và nguồn linh kiện trước khi trả // checking the piece\'s age and part sources before return')

_profile('mother_baby', 'Thanh Mai | Đức Huy | Tú Anh',
    'Hội tiểu thương · chủ tiệm Mây Nhỏ // Traders association · Little Cloud shop owner',
    'quà đúng độ tuổi, đủ đơn và đổi trả rõ ràng // age-appropriate gifts, complete orders, and clear returns',
    'nhãn độ tuổi | gói quà | đối soát đơn // age labels | gift wrapping | order reconciliation',
    'Đoàn khách đặt quà cho hai nhóm tuổi; đồ chơi hạt nhỏ đang xếp lẫn vào nhóm nhỏ tuổi. // A group ordered gifts for two age groups; small-parts toys are mixed into the younger group.',
    'Giao {a} kiểm nhãn tuổi, {b} gói sau khi duyệt, {c} đối chiếu từng nhóm với đơn khách. // Have {a} check age labels, {b} wrap approved items, and {c} reconcile each group against the order.',
    'Hộp quà đã đẹp nhưng thiếu một món và không có phiếu đổi trả như đã hẹn. // The gift box looks good but lacks one item and the promised return slip.',
    'Mở kiểm cùng phiếu đơn, bổ sung món và phiếu đổi trả rồi kiểm lại trước giao. // Check against the order, add the missing item and return slip, and verify before delivery.',
    'đã phát hiện nhầm nhóm tuổi và có phiếu xác nhận đủ quà // caught an age-group mismatch and documented a complete delivery',
    'kiểm nhãn độ tuổi // age-label checks')

_profile('pharmacy', 'Khánh An | Minh Khang | Bích Ngọc',
    'Dược sĩ phụ trách quầy // Supervising pharmacist',
    'đối chiếu phiếu, đúng mã và chuyển dược sĩ khi vượt phạm vi // checking slips and product codes and referring beyond-scope questions to the pharmacist',
    'đối chiếu phiếu | kiểm mã và lô | hướng dẫn quy trình quầy // slip verification | product and batch checks | counter procedure guidance',
    'Quầy có phiếu thiếu thông tin và một khách hỏi thay sản phẩm; người mới chưa biết khi nào cần dược sĩ. // The counter has an incomplete slip and a substitution question; a new colleague is unsure when to involve the pharmacist.',
    'Giao {a} hỏi rõ phiếu, {b} giữ lô chờ kiểm, {c} hướng dẫn người mới chuyển câu hỏi thay sản phẩm cho dược sĩ. // Have {a} clarify the slip, {b} hold the batch for checks, and {c} coach the newcomer to refer substitution questions to the pharmacist.',
    'Mã trên túi khác phiếu; đồng nghiệp nói bao bì tương tự nên chắc đúng. // The bag code differs from the slip; a colleague assumes it is correct because the packaging looks similar.',
    'Dừng giao, đối chiếu mã và lô với phiếu; nhờ dược sĩ xác nhận phần chưa rõ rồi kiểm lại. // Hold handover, reconcile codes and batches against the slip, and ask the pharmacist to confirm unresolved details before rechecking.',
    'đã nhận ra phiếu thiếu và chuyển dược sĩ, lưu xác nhận đúng mã // identified an incomplete slip, referred it to the pharmacist, and documented the correct code',
    'xác nhận phiếu và mã lô // slip and batch-code confirmation')

_profile('accounting', 'Vân Anh | Tuấn Kiệt | Ngọc Hà',
    'Chị Vân · quản lý văn phòng // Vân · office manager',
    'đối soát có chứng từ và bảo mật hồ sơ khách // evidence-based reconciliation and confidential client records',
    'đọc chứng từ | tìm sai lệch | bàn giao hồ sơ // source-document review | discrepancy investigation | file handover',
    'Khách đưa sổ quỹ lệch với biên nhận; có một trang bản gốc chưa gửi. // A client\'s cashbook differs from the receipts and one original page is missing.',
    'Giao {a} lập danh sách chứng từ, {b} khoanh sai lệch, {c} xin trang còn thiếu qua kênh riêng rồi cùng đối soát. // Have {a} list source documents, {b} isolate discrepancies, and {c} request the missing page privately before joint reconciliation.',
    'Tổng sổ khớp sau khi một dòng được sửa nhưng không ghi nguồn sửa. // The ledger total matches after one entry was changed without recording the source.',
    'Yêu cầu chứng từ gốc và dấu vết sửa; đối chiếu lại dòng thay đổi trước khi ký bàn giao. // Request the source document and change record; reconcile the amended entry before handover.',
    'đã tìm biên nhận gốc giải thích chênh lệch, lưu dấu vết sửa đầy đủ // found the original receipt explaining the discrepancy and retained the correction trail',
    'chứng từ cho dòng điều chỉnh // supporting documents for the adjustment')

_profile('customer_care', 'Phương Linh | Gia Huy | Thảo Vy',
    'Trưởng ca dịch vụ // Service shift supervisor',
    'lời hẹn chính xác, theo dõi đến cùng và chuyển cấp đúng // accurate commitments, complete follow-up, and appropriate escalation',
    'lắng nghe phản ánh | kiểm lịch sử yêu cầu | theo dõi lời hẹn // listening to complaints | checking request history | tracking commitments',
    'Ba khách hỏi cùng lỗi, một người đã được hẹn gọi lại nhưng chưa ai nhận trách nhiệm. // Three customers report the same issue; one was promised a callback with no assigned owner.',
    'Giao {a} xác nhận nhu cầu, {b} gom lịch sử lỗi, {c} nhận theo dõi lời hẹn; thống nhất mốc chuyển cấp. // Have {a} confirm needs, {b} gather issue histories, and {c} own callbacks; agree on an escalation checkpoint.',
    'Phiếu ghi đã giải quyết nhưng khách chỉ nhận lời hứa, chưa có kết quả kiểm chứng. // A ticket says resolved, but the customer only received a promise, not a verified result.',
    'Mở lại phiếu, kiểm kết quả với khách và giao người theo dõi đến khi đủ điều kiện đóng. // Reopen the ticket, verify the result with the customer, and assign follow-up until closure is justified.',
    'đã giữ đúng hẹn gọi lại và có khách xác nhận vấn đề được giải quyết // kept the callback commitment and obtained customer confirmation that the issue was resolved',
    'xác nhận kết quả từ khách // customer confirmation of the outcome')

_profile('teacher', 'Thu Hương | Hải Đăng | Minh Thư',
    'Tổ chuyên môn · ban giám hiệu // Subject team · school leadership',
    'bài dạy đúng mục tiêu và đánh giá học sinh công bằng // lessons meeting learning goals and fair student assessment',
    'thiết kế bài học | hỗ trợ học sinh | xây tiêu chí đánh giá // lesson design | learner support | assessment criteria',
    'Tổ chuẩn bị tiết chuyên đề có học sinh cần hỗ trợ riêng; giáo viên mới chỉ có một đề chung. // The team is preparing a demonstration lesson with a student needing individual support; a new teacher has only one standard task.',
    'Giao {a} chốt mục tiêu, {b} chuẩn bị hỗ trợ phù hợp, {c} thống nhất tiêu chí rồi cùng duyệt bài. // Have {a} set objectives, {b} prepare suitable support, and {c} align criteria before reviewing the lesson together.',
    'Hai bài có cách giải tương đương bị chấm khác nhau vì giáo viên dùng hai tiêu chí. // Two equivalent solutions received different marks because teachers used different criteria.',
    'Đối chiếu tiêu chí chung, rà lại các bài liên quan và giải thích điều chỉnh riêng với học sinh. // Apply the agreed criteria, review affected work, and explain corrections privately to students.',
    'đã hỗ trợ học sinh đúng nhu cầu và lưu bài đánh giá theo tiêu chí chung // supported a learner\'s needs and retained assessments using the shared criteria',
    'tiêu chí và bài làm đối chiếu // criteria and supporting student work')

_profile('tour_guide', 'Bảo Trân | Quốc Hưng | Kim Ngân',
    'Điều hành tour // Tour operations supervisor',
    'đủ đoàn, lịch trình rõ và xử lý thay đổi có trách nhiệm // keeping the group together, clear itineraries, and responsible changes',
    'điểm danh đoàn | trao đổi điểm đến | điều chỉnh lịch // group headcounts | destination communication | itinerary adjustments',
    'Điểm tham quan đóng sớm; một nhóm khách cần thêm thời gian di chuyển và xe đang chờ. // An attraction closes early; some guests need more travel time while the coach waits.',
    'Giao {a} kiểm đủ người, {b} xác minh giờ mở cửa, {c} đề xuất lịch thay thế với điều hành rồi báo đoàn. // Have {a} check the group, {b} verify opening hours, and {c} agree on an alternative with operations before informing guests.',
    'Bảng điểm danh ghi đủ nhưng khách ở điểm hẹn phụ chưa xác nhận lên xe. // The headcount sheet is complete, but a guest at a secondary meeting point has not been confirmed aboard.',
    'Giữ việc xác nhận rời điểm, đối chiếu danh sách và liên lạc khách qua điều hành trước khi chốt đoàn. // Withhold departure confirmation, reconcile the list, and contact the guest through operations before closing the headcount.',
    'đã tìm đúng khách ở điểm hẹn phụ và cập nhật lịch được điều hành xác nhận // located the guest at the secondary meeting point and obtained approval for the revised itinerary',
    'xác nhận đủ đoàn // confirmed group headcounts')

_profile('milk_tea', 'Hồng Anh | Nhật Minh | Bảo Ngọc',
    'Hội chủ quán · giám khảo pha chế // Cafe owners association · beverage judge',
    'đúng công thức, vệ sinh và nhãn đơn rõ // correct recipes, hygiene, and clear order labels',
    'đối chiếu công thức | tổ chức quầy sạch | kiểm nhãn ly // recipe verification | hygienic counter organization | cup-label checks',
    'Đơn họp có nhiều mức đường và yêu cầu tránh một nguyên liệu; người mới đã xếp cốc chung. // A meeting order has several sugar levels and an ingredient-avoidance request; a new colleague has grouped all cups together.',
    'Giao {a} kiểm công thức từng nhóm, {b} tách dụng cụ theo yêu cầu, {c} so nhãn và phiếu trước giao. // Have {a} check each recipe group, {b} separate tools as required, and {c} compare labels against tickets before delivery.',
    'Số ly đủ nhưng hai nhãn mức đường bị đổi chỗ, chưa xác định ly có yêu cầu riêng. // The cup count is correct, but two sugar labels are swapped and the special-request cup is unidentified.',
    'Giữ lô chờ kiểm, đối chiếu phiếu và làm lại phần không xác minh được rồi kiểm nhãn cùng người giao. // Hold the batch, check tickets, remake unverified drinks, and verify labels with the delivery colleague.',
    'đã giữ riêng đơn yêu cầu đặc biệt và đối chiếu đủ nhãn trước giao // kept the special order separate and verified all labels before handover',
    'đối chiếu công thức từng ly // recipe checks for each cup')

_profile('restaurant', 'Mỹ Duyên | Thành Đạt | Hoài An',
    'Hội đầu bếp · chủ quán mì cay // Chefs association · spicy-noodle restaurant owner',
    'đúng món, mức cay và an toàn thực phẩm // correct dishes, spice levels, and food safety',
    'đọc phiếu món | tổ chức bếp | kiểm món ra bàn // reading meal tickets | kitchen organization | checking plated orders',
    'Đoàn khách đặt nhiều mức cay, một bàn báo tránh nguyên liệu trong nước dùng. // A group ordered several spice levels, and one table asked to avoid an ingredient in the broth.',
    'Giao {a} xác nhận từng phiếu, {b} kiểm khả năng đáp ứng yêu cầu riêng, {c} kiểm món theo số bàn trước phục vụ. // Have {a} confirm tickets, {b} verify whether the special request can be met, and {c} match dishes to tables before service.',
    'Hai tô nhìn giống nhau nhưng phiếu mức cay khác; phụ bếp chưa đánh dấu tô riêng. // Two bowls look alike but have different spice tickets; the kitchen assistant has not marked the special bowl.',
    'Dừng đưa hai tô ra bàn, xác minh với bếp và làm lại phần không chắc; kiểm đúng phiếu trước giao. // Hold both bowls, verify with the kitchen, remake anything uncertain, and check tickets before serving.',
    'đã phát hiện nhầm mức cay trước phục vụ và xác nhận lại yêu cầu riêng với bếp // caught a spice-level mismatch before service and reconfirmed the special request with the kitchen',
    'đối chiếu món với phiếu bàn // dish-to-table ticket checks')

_profile('cafe_bakery', 'Khánh Ly | Thiên Phúc | Ngọc Ánh',
    'Trưởng bếp · hội nghề bánh // Head baker · baking association',
    'mẻ bánh đạt, đồ uống đúng và giao theo thứ tự hẹn // acceptable batches, correct drinks, and delivery in promised order',
    'kiểm mẻ bánh | pha đồ uống | ghép đơn quầy // checking baking batches | drink preparation | combining counter orders',
    'Bánh sinh nhật đặt trước trùng ca cà phê đông; mẻ bánh mới còn chờ kiểm chất lượng. // A preordered birthday cake overlaps with a busy coffee shift; a new batch still awaits quality checks.',
    'Giao {a} kiểm bánh trước trang trí, {b} giữ luồng đồ uống, {c} ghép đơn theo giờ hẹn và kiểm đủ món. // Have {a} inspect cakes before decorating, {b} maintain drink service, and {c} combine and check orders by promised time.',
    'Hộp bánh đúng tên khách nhưng lời ghi trên bánh khác mẫu đã duyệt. // The cake box has the correct customer name, but the inscription differs from the approved design.',
    'Đối chiếu mẫu, sửa phần ghi và kiểm lại cùng phiếu đặt trước khi đóng hộp. // Compare the approved design, correct the inscription, and recheck the order before boxing.',
    'đã phát hiện sai lời ghi trên bánh và bàn giao đúng mẫu được khách duyệt // caught an incorrect cake inscription and delivered the approved design',
    'duyệt mẫu và kiểm mẻ bánh // design approval and batch checks')

_profile('florist', 'Lan Hương | Anh Tú | Mỹ Hạnh',
    'Hội hoa · chủ cửa hàng // Florists association · shop owner',
    'hoa tươi, đúng mẫu và giao đúng thời điểm sự kiện // fresh flowers, approved designs, and timely event delivery',
    'chọn hoa | dựng bố cục | điều phối giao hoa // flower selection | arrangement design | flower delivery coordination',
    'Hai sự kiện cùng buổi cần hoa khác màu; một lô vừa nhập có cành dập. // Two events need different color schemes on the same morning; a new delivery contains damaged stems.',
    'Giao {a} loại cành không đạt, {b} kiểm mẫu từng sự kiện, {c} chia giờ giao và chụp đối chiếu trước xuất. // Have {a} reject damaged stems, {b} check each event design, and {c} schedule deliveries with comparison photos before dispatch.',
    'Bó hoa đẹp nhưng thiệp ghi tên người nhận của đơn khác. // The bouquet looks beautiful, but its card names the recipient of another order.',
    'Tách hai đơn, kiểm tên thiệp và địa điểm với phiếu gốc rồi kiểm chéo trước giao. // Separate the orders, verify card names and venues against the original tickets, and cross-check before delivery.',
    'đã đổi cành dập và xác nhận đúng thiệp, đúng địa điểm sự kiện // replaced damaged stems and confirmed the correct card and event venue',
    'đối chiếu thiệp và mẫu đã duyệt // card checks and approved-design comparison')

_profile('grocery', 'Thanh Nga | Hữu Phước | Ngọc Lan',
    'Cô Ba · chủ tiệm tạp hóa // Ba · grocery owner',
    'hạn dùng rõ, cân đúng và hóa đơn khớp // clear expiry dates, accurate weights, and matching receipts',
    'kiểm hạn dùng | cân và tính giá | đối soát kho // expiry-date checks | weighing and pricing | stock reconciliation',
    'Đơn sỉ cuối tuần cần lấy hàng từ hai lô; lô gần hạn đang nằm sau kệ. // A weekend wholesale order needs stock from two batches; the near-expiry batch is at the back of the shelf.',
    'Giao {a} kiểm hạn và điều kiện bán, {b} cân tính theo giá đã báo, {c} đối chiếu số lượng xuất rồi cùng kiểm hóa đơn. // Have {a} check expiry and sale suitability, {b} weigh at the agreed price, and {c} reconcile outgoing quantities before checking the receipt together.',
    'Tổng hóa đơn đúng nhưng một mặt hàng tính sai đơn giá, bù trừ bởi lỗi số lượng ở dòng khác. // The invoice total matches, but one item has the wrong unit price offset by a quantity error on another line.',
    'So lại từng dòng với hàng thực và bảng giá, sửa cả hai lỗi rồi xác nhận lại với khách. // Compare every line with the goods and price list, correct both errors, and reconfirm with the customer.',
    'đã phát hiện lô gần hạn, thông tin rõ với khách và lập hóa đơn đúng từng dòng // identified a near-expiry batch, informed the customer, and prepared an accurate itemized receipt',
    'kiểm hạn và giá từng mặt hàng // item-level expiry and price checks')

_profile('repair', 'Hải Sơn | Đình Long | Xuân Mai',
    'Trưởng xưởng sửa đồ // Repair workshop supervisor',
    'chẩn đoán có căn cứ, báo giá rõ và thử sau sửa // evidence-based diagnosis, clear estimates, and post-repair testing',
    'chẩn đoán lỗi | sửa theo quy trình | kiểm thử bàn giao // fault diagnosis | procedural repair | handover testing',
    'Hai máy cùng biểu hiện mất nguồn nhưng lịch sử khác nhau; khách cần báo giá trước thay linh kiện. // Two machines show the same power fault but have different histories; customers need estimates before parts are replaced.',
    'Giao {a} chẩn đoán riêng từng máy, {b} sửa sau khi khách duyệt, {c} kiểm thử và ghi kết quả bàn giao. // Have {a} diagnose each machine separately, {b} repair after approval, and {c} test and document the handover.',
    'Máy chạy lại nhưng phiếu không có kết quả thử tải và linh kiện thay chưa nằm trong báo giá được duyệt. // The machine runs again, but no load-test result is recorded and the replaced part was not in the approved estimate.',
    'Rà phạm vi khách đã duyệt, làm rõ thay đổi và hoàn tất kiểm thử trước khi xác nhận sửa xong. // Review the approved scope, resolve the change, and complete testing before confirming the repair.',
    'đã tìm đúng nguyên nhân, xin duyệt báo giá và lưu kiểm thử sau sửa // found the cause, obtained estimate approval, and recorded post-repair tests',
    'báo giá đã duyệt và kết quả thử // approved estimates and test results')

_profile('farm', 'Đức Thịnh | Thảo Nguyên | Minh Châu',
    'Chú Tám · tổ trưởng hợp tác xã rau // Tám · vegetable cooperative leader',
    'lô thu hoạch đạt chất lượng và nhật ký nguồn gốc thật // quality harvest batches and truthful provenance logs',
    'kiểm độ trưởng thành | phân loại nông sản | ghi nhật ký lô // maturity checks | produce grading | batch records',
    'Hợp đồng bếp cần rau đồng đều nhưng hai luống chín khác nhau; người mới muốn thu hết để đủ số. // A kitchen contract needs uniform produce, but two beds mature differently; a newcomer wants to harvest everything to fill the quantity.',
    'Giao {a} chọn luống đạt, {b} phân loại sau thu, {c} ghi đúng lô và báo thiếu số lượng nếu có. // Have {a} select ready beds, {b} grade the harvest, and {c} record batches accurately and report any shortfall.',
    'Thùng rau đủ cân nhưng lẫn rau dập; nhật ký lại ghi tất cả loại A. // The crate meets its target weight but contains bruised produce while the log labels everything grade A.',
    'Phân loại lại, cập nhật cân và nhật ký đúng thực tế, thống nhất với bên nhận rồi kiểm lô trước giao. // Regrade the produce, correct weights and logs, agree with the recipient, and inspect before delivery.',
    'đã tách đúng rau dập, ghi thật chất lượng lô và bàn giao được xác nhận // separated bruised produce, recorded actual batch quality, and obtained handover confirmation',
    'nhật ký nguồn gốc và phân loại lô // provenance logs and batch grading')

_profile('delivery', 'Hữu Tín | Phúc Lâm | Thanh Trúc',
    'Chị Hạnh · điều phối viên bưu cục // Hạnh · delivery depot coordinator',
    'đúng người, đủ kiện, đối soát COD và đi an toàn // correct recipients, complete parcels, reconciled cash on delivery, and safe travel',
    'kiểm địa chỉ | sắp xếp tuyến | đối soát COD // address verification | route planning | cash-on-delivery reconciliation',
    'Tuyến có hai người trùng tên và một kiện COD; đường thường đi đang có thông báo gián đoạn. // The route has two recipients with the same name and a cash-on-delivery parcel; the usual road is disrupted.',
    'Giao {a} xác minh địa chỉ, {b} chọn tuyến an toàn, {c} giữ phiếu COD và cùng kiểm kiện trước xuất. // Have {a} verify addresses, {b} choose a safe route, and {c} maintain COD records and join the dispatch check.',
    'Ứng dụng ghi giao đủ nhưng chữ ký người nhận không khớp phiếu, tiền COD thiếu đối chiếu. // The app marks delivery complete, but the signature does not match the recipient record and COD is unreconciled.',
    'Xác minh bàn giao qua điều phối, đối chiếu người nhận và COD rồi mới chốt tuyến. // Verify handover through dispatch, reconcile the recipient and COD, and only then close the route.',
    'đã xác minh hai địa chỉ trùng tên và đối soát COD đủ chứng từ // verified two same-name addresses and reconciled COD with supporting records',
    'xác nhận người nhận và COD // recipient and COD confirmation')

_profile('homestay', 'Diễm Quỳnh | Huy Hoàng | Thu Hà',
    'Chủ homestay · hiệp hội lưu trú // Homestay owner · accommodation association',
    'phòng sạch, đặt phòng khớp và phản ánh được theo dõi // clean rooms, accurate bookings, and tracked complaints',
    'kiểm phòng | đối chiếu đặt chỗ | hỗ trợ khách // room inspection | booking reconciliation | guest support',
    'Đoàn đến sớm trong khi hai phòng vừa trả; một phòng có yêu cầu giường khác. // A group arrives early while two rooms are being turned over; one booking has a different bed request.',
    'Giao {a} kiểm phòng sau vệ sinh, {b} ghép đúng đặt chỗ, {c} báo thời gian chờ thật và theo dõi nhu cầu riêng. // Have {a} inspect cleaned rooms, {b} match bookings, and {c} communicate honest waiting times and track special requests.',
    'Phòng được đánh dấu sẵn sàng nhưng khách trước còn để tài sản trong ngăn kéo. // A room is marked ready, but a previous guest\'s belongings remain in a drawer.',
    'Giữ phòng chờ kiểm, lập bàn giao tài sản theo quy trình và kiểm lại toàn phòng trước đón khách. // Hold the room, log the found property under procedure, and reinspect before welcoming the next guest.',
    'đã giữ đúng yêu cầu giường và xử lý tài sản thất lạc có biên nhận // met the bed request and handled found property with a receipt',
    'kiểm phòng và đối chiếu đặt chỗ // room checks and booking reconciliation')

_profile('pet_care', 'Hoài Thương | Gia Bảo | Nhật Vy',
    'Trưởng ca chăm thú // Pet-care shift supervisor',
    'chăm đúng loài, nhận diện bất thường và giao nhận rõ // species-appropriate care, recognizing abnormalities, and clear handovers',
    'đọc hồ sơ chăm sóc | quan sát hành vi | ghi nhận bàn giao // care-record review | behavior observation | handover records',
    'Hai thú nội trú có nếp ăn khác nhau; một bé mới tới tỏ ra căng thẳng và cần theo dõi. // Two boarding pets have different feeding routines; a new arrival appears distressed and needs observation.',
    'Giao {a} đối chiếu hướng dẫn chủ, {b} theo dõi dấu hiệu và báo người phụ trách, {c} giữ nhật ký riêng từng bé. // Have {a} check owner instructions, {b} observe and report signs to the supervisor, and {c} maintain individual logs.',
    'Phiếu ghi đã ăn nhưng bát vẫn nguyên; người mới định ghi bình thường để đủ mẫu. // The record says the pet ate, but the bowl is untouched; a newcomer wants to mark everything normal.',
    'Ghi đúng quan sát, báo người phụ trách theo quy trình và kiểm lại việc chăm trước bàn giao cho chủ. // Record actual observations, notify the supervisor under procedure, and verify care before owner handover.',
    'đã nhận ra thay đổi hành vi và báo đúng người, lưu nhật ký được chủ xác nhận // noticed a behavior change, informed the right person, and retained a log acknowledged by the owner',
    'nhật ký chăm riêng từng thú // individual pet-care logs')

_profile('salon', 'Mai Phương | Tuấn Anh | Bảo Yến',
    'Chủ salon · hội nghề tóc // Salon owner · hairdressing association',
    'thống nhất mẫu tóc, kỹ thuật phù hợp và dụng cụ sạch // agreed hairstyles, suitable technique, and clean tools',
    'tư vấn mẫu | chuẩn bị dụng cụ | kiểm hoàn thiện tóc // style consultation | tool preparation | final hairstyle checks',
    'Khách đặt mẫu khó, có ảnh tham khảo nhưng chưa thống nhất độ dài; thợ mới đang chuẩn bị làm. // A client requested a complex style with a reference photo but has not agreed on length; a new stylist is preparing to begin.',
    'Giao {a} chốt độ dài với khách, {b} chuẩn bị dụng cụ đúng vệ sinh, {c} cùng thợ chính kiểm từng mốc hoàn thiện. // Have {a} agree on length, {b} prepare hygienic tools, and {c} check completion stages with the lead stylist.',
    'Tóc đã tạo kiểu nhưng khác độ dài được ghi trên phiếu tư vấn. // The hair is styled, but its length differs from the consultation record.',
    'Đối chiếu phiếu với khách, báo thợ phụ trách và thống nhất phương án khắc phục trước xác nhận hài lòng. // Review the consultation record with the client, notify the lead stylist, and agree on a remedy before recording satisfaction.',
    'đã tư vấn rõ giới hạn mẫu và có khách xác nhận kết quả phù hợp // explained style limitations clearly and obtained client confirmation of a suitable result',
    'phiếu thống nhất mẫu và kiểm dụng cụ // style agreement and tool checks')

_profile('corp_accounting', 'Đức Anh | Phương Thảo | Khánh Hòa',
    'Chị Hạnh · kế toán trưởng // Hạnh · chief accountant',
    'hạch toán có căn cứ và kiểm soát sai lệch doanh nghiệp // supported journal entries and company discrepancy controls',
    'kiểm chứng từ | đối soát công nợ | soát xét bút toán // document checks | receivables reconciliation | journal review',
    'Bộ hồ sơ tháng có hóa đơn và biên bản giao hàng khác kỳ; hạn khóa sổ đang tới. // Monthly files contain an invoice and delivery record from different periods; closing is approaching.',
    'Giao {a} kiểm ngày và hồ sơ, {b} đối chiếu công nợ, {c} lập điểm cần soát xét để kế toán trưởng duyệt. // Have {a} check dates and documents, {b} reconcile balances, and {c} list review issues for the chief accountant.',
    'Bút toán cân nhưng mã đối tượng sai, khiến sổ chi tiết không khớp biên bản công nợ. // The entry balances, but the counterparty code is wrong and the subledger differs from the balance confirmation.',
    'Đối chiếu chứng từ và mã đối tượng, lập điều chỉnh có duyệt rồi kiểm lại sổ chi tiết. // Check documents and counterparty codes, prepare an approved correction, and recheck the subledger.',
    'đã tìm sai mã đối tượng và lưu điều chỉnh được kế toán trưởng duyệt // found a wrong counterparty code and retained a correction approved by the chief accountant',
    'chứng từ và dấu vết soát xét // supporting documents and review trails')

_profile('tax_payroll', 'Hồng Nhung | Thanh Tùng | Minh Ngọc',
    'Chị Hồng · kế toán trưởng // Hồng · chief accountant',
    'dữ liệu lương có căn cứ, hồ sơ đủ và bảo mật // supported payroll data, complete records, and confidentiality',
    'đối chiếu chấm công | kiểm bảng tính | bảo mật hồ sơ // attendance reconciliation | calculation checks | records confidentiality',
    'Kỳ lương có bảng chấm công điều chỉnh muộn; người mới muốn dùng bản cũ để kịp gửi. // Payroll has a late attendance correction; a newcomer wants to use the old version to send it on time.',
    'Giao {a} xác minh bản chấm công, {b} so tác động bảng tính, {c} kiểm quyền nhận trước khi trình duyệt. // Have {a} verify attendance versions, {b} check calculation effects, and {c} verify recipients before approval.',
    'Tổng lương khớp nhưng file xuất có cột thông tin cá nhân gửi cho người không phụ trách. // Payroll totals match, but the export includes personal data for recipients without responsibility for it.',
    'Giữ file chưa gửi, kiểm phạm vi người nhận và dữ liệu cần thiết, xuất lại rồi soát xét theo quyền. // Hold the export, review recipients and necessary data, regenerate the file, and review access.',
    'đã phát hiện bản chấm công cũ và giao đúng bảng lương qua kênh hạn chế quyền // caught an outdated attendance sheet and delivered the correct payroll through an access-restricted channel',
    'bản chấm công được duyệt và kiểm quyền nhận // approved attendance records and recipient-access checks')

_profile('group_accounting', 'Minh Tú | Hoàng Yến | Quốc Việt',
    'Chị Mai Anh · giám đốc tài chính tập đoàn // Mai Anh · group finance director',
    'đối chiếu nội bộ và điều chỉnh hợp nhất có dấu vết // intercompany reconciliation and traceable consolidation adjustments',
    'chuẩn hóa dữ liệu đơn vị | đối chiếu nội bộ | kiểm bảng hợp nhất // entity-data standardization | intercompany reconciliation | consolidation review',
    'Hai công ty gửi số dư nội bộ lệch nhau và dùng phiên bản biểu mẫu khác. // Two entities report mismatched intercompany balances using different template versions.',
    'Giao {a} chuẩn hóa bản gửi, {b} đối chiếu từng cặp, {c} theo dõi chênh lệch chờ xác nhận trước hợp nhất. // Have {a} standardize submissions, {b} reconcile each pair, and {c} track differences awaiting confirmation before consolidation.',
    'Bảng hợp nhất cân nhờ một dòng bù trừ nhưng chưa có xác nhận từ đơn vị đối ứng. // The consolidation balances because of an offsetting entry without confirmation from the counterparty entity.',
    'Tách dòng chưa đủ căn cứ, xin xác nhận hai bên và kiểm điều chỉnh trước khi duyệt báo cáo. // Flag the unsupported entry, obtain both entities\' confirmations, and verify the adjustment before approval.',
    'đã đối chiếu đủ hai phía và lưu bảng điều chỉnh hợp nhất có nguồn // reconciled both sides and retained sourced consolidation adjustments',
    'xác nhận giao dịch nội bộ hai phía // bilateral intercompany confirmations')

_profile('clothing', 'Ngọc Diệp | Anh Khoa | Thùy Linh',
    'Chị Vy · chủ shop // Vy · clothing shop owner',
    'tư vấn size phù hợp, đơn đúng và đổi trả công bằng // suitable size advice, accurate orders, and fair returns',
    'đo và tư vấn size | kiểm mẫu màu | xử lý đổi trả // sizing advice | style and color checks | return handling',
    'Đơn đồng phục có nhiều size; khách xin đổi hai mẫu chưa tháo nhãn và người mới chưa rõ chính sách. // A uniform order contains several sizes; a customer wants to exchange two tagged items and a newcomer is unsure of the policy.',
    'Giao {a} xác nhận bảng size, {b} kiểm mẫu theo đơn, {c} đối chiếu điều kiện đổi và hướng dẫn người mới. // Have {a} confirm sizes, {b} check ordered styles, and {c} verify exchange conditions and coach the newcomer.',
    'Túi ghi đúng size nhưng áo bên trong mang nhãn khác; phiếu đổi chưa cập nhật. // The bag lists the right size, but the garment label differs and the exchange slip is outdated.',
    'Mở kiểm nhãn thực, ghép lại đúng đơn và cập nhật phiếu đổi rồi xác nhận với khách. // Check actual garment labels, rebuild the order, update the exchange slip, and confirm with the customer.',
    'đã tìm lỗi ghép size và xử lý đổi theo chính sách đã công bố // found a size-packing error and handled the exchange under the published policy',
    'kiểm nhãn size và phiếu đổi // size-label and exchange-slip checks')

_profile('pet_shop', 'Ngọc Hân | Thành Vinh | Quỳnh Anh',
    'Hội cửa hàng thú cưng // Pet shop association',
    'tư vấn hàng phù hợp loài và bảo quản đúng nhãn // species-appropriate product advice and label-compliant storage',
    'đọc nhãn sản phẩm | kiểm bảo quản | đối soát đơn thú cưng // product-label review | storage checks | pet-product order reconciliation',
    'Khách đặt thức ăn cho hai loài khác nhau, một bao vừa nhập có dấu hiệu hỏng bao bì. // A customer ordered food for two species, and one newly arrived bag has damaged packaging.',
    'Giao {a} đối chiếu loài và nhãn, {b} tách bao hỏng chờ xử lý, {c} kiểm đủ đơn trước khi xác nhận. // Have {a} compare species and labels, {b} isolate damaged packaging, and {c} verify the order before confirmation.',
    'Đơn đủ số bao nhưng một mã không phù hợp loài khách đã nêu. // The bag count is correct, but one product code does not match the species the customer specified.',
    'Giữ đơn, đối chiếu nhãn với nhu cầu đã ghi và đổi mã phù hợp; kiểm lại điều kiện bảo quản. // Hold the order, compare labels with recorded needs, replace the unsuitable item, and recheck storage conditions.',
    'đã phát hiện nhầm mã theo loài và thay đúng hàng có nhãn nguyên vẹn // caught a species mismatch and supplied the correct product with intact labeling',
    'đối chiếu loài và điều kiện bảo quản // species and storage-condition checks')

_profile('tra_da', 'Bích Thủy | Đức Toàn | Hồng Vân',
    'Bà Lựu · chủ quán trà đá // Lựu · iced-tea stall owner',
    'phục vụ sạch, đủ món và bố trí gọn đúng chỗ // clean service, complete orders, and tidy use of the permitted area',
    'pha trà | vệ sinh ly | sắp chỗ ngồi // tea preparation | cup hygiene | seating organization',
    'Ca đông khách trong khu vực được phép bán; bàn mới xếp chắn lối đi và ly sạch gần hết. // The permitted stall area is busy; new tables obstruct the walkway and clean cups are running low.',
    'Giao {a} giữ đơn trà, {b} bổ sung ly sạch, {c} xếp lại bàn trong phạm vi hợp lệ và kiểm lối đi. // Have {a} manage tea orders, {b} replenish clean cups, and {c} rearrange tables within the allowed area and check access.',
    'Bàn đã lau nhưng khay ly dùng rồi đặt lẫn với ly sạch. // Tables have been wiped, but used cups are mixed with clean ones.',
    'Tách khay bẩn, làm sạch đúng quy trình và kiểm lại khu phục vụ trước tiếp khách. // Separate dirty trays, clean under procedure, and recheck the service area before serving.',
    'đã giữ lối đi thông thoáng và kiểm đủ ly sạch trong ca đông // maintained clear access and verified clean-cup availability during the rush',
    'kiểm vệ sinh và vị trí bàn // hygiene and table-position checks')

_profile('fruit', 'Thanh Xuân | Trọng Nghĩa | Mỹ Linh',
    'Dì Tư · chủ sạp trái cây // Tư · fruit stall owner',
    'phân loại thật, cân đúng và giữ độ tươi // honest grading, accurate weighing, and freshness',
    'chọn độ chín | kiểm cân | xếp giỏ quà // ripeness selection | scale checks | gift-basket packing',
    'Đơn giỏ quà cần trái chín vừa; lô mới có quả dập và một khách muốn giao xa. // Gift baskets need moderately ripe fruit; a new batch contains bruised fruit and one customer needs long-distance delivery.',
    'Giao {a} chọn độ chín theo ngày nhận, {b} kiểm cân từng giỏ, {c} đóng gói tránh dập và ghi rõ chất lượng. // Have {a} choose ripeness for the arrival date, {b} check basket weights, and {c} pack against bruising and describe quality honestly.',
    'Giỏ đủ cân nhưng quả dập bị giấu phía dưới lớp trang trí. // The basket has the right weight, but bruised fruit is hidden under decorations.',
    'Mở giỏ, phân loại lại và trao đổi thay thế với khách; cân kiểm sau khi đóng lại. // Open the basket, regrade the fruit, agree on replacements with the customer, and reweigh after repacking.',
    'đã loại quả dập và giao giỏ được khách xác nhận đúng cân, đúng độ chín // removed bruised fruit and delivered baskets confirmed for weight and ripeness',
    'kiểm cân và phân loại độ chín // weight checks and ripeness grading')

_profile('post_office', 'Thanh Bình | Ngọc Quế | Đức Minh',
    'Trưởng bưu cục // Post office manager',
    'cân cước đúng, giấy tờ đủ và bưu gửi đúng tuyến // correct weights and postage, complete documents, and correct routing',
    'kiểm giấy tờ | cân tính cước | phân tuyến bưu gửi // document checks | weighing and postage | parcel routing',
    'Ca nhận bưu gửi đoàn có thư cần xác nhận và kiện hàng khai thiếu nội dung; quầy đang đông. // A group shipment includes tracked letters and a parcel with an incomplete contents declaration during a busy shift.',
    'Giao {a} kiểm khai báo, {b} cân tính cước sau xác minh, {c} tách tuyến và kiểm mã trước bàn giao. // Have {a} check declarations, {b} weigh and price verified items, and {c} sort routes and verify codes before handover.',
    'Túi tuyến đã niêm nhưng một mã bưu gửi xuất hiện trong hai danh sách nhận. // A route bag is sealed, but one parcel code appears on two intake lists.',
    'Giữ túi chờ đối soát, kiểm mã thực và danh sách gốc, sửa biên bản rồi xác nhận bàn giao lại. // Hold the bag, reconcile actual codes against original lists, correct the record, and reconfirm handover.',
    'đã tìm mã ghi trùng và đối chiếu đủ giấy tờ, cước, tuyến trước giao // found a duplicate code and verified documents, postage, and routing before handover',
    'đối chiếu mã và giấy nhận // code reconciliation and intake receipts')

_profile('pagoda', 'Thiện An | Minh Tâm | Diệu Hòa',
    'Thầy Huệ Minh · ban công quả // Huệ Minh · community service committee',
    'hoàn thành công quả, giữ nếp và hỗ trợ cộng đồng // completing community service, respecting routines, and helping others',
    'chuẩn bị suất ăn | giữ lối đi sạch | đón người cần hỗ trợ // meal preparation | keeping paths clear | welcoming people needing support',
    'Buổi công quả có người cao tuổi tới nhận suất ăn; khu chia đồ chưa phân luồng và người mới chưa biết việc. // Older visitors arrive for community meals; the serving area has no clear flow and new volunteers need guidance.',
    'Giao {a} kiểm suất ăn, {b} giữ lối đi an toàn, {c} đón người cần giúp và hướng dẫn người mới cùng làm. // Have {a} check meals, {b} keep paths safe, and {c} welcome those needing help and guide newcomers.',
    'Bảng công quả ghi xong nhưng lối tới nơi nhận suất ăn còn thùng đồ chắn người đi lại. // The service sheet says complete, but boxes still block access to the meal collection point.',
    'Nhờ tổ chuyển thùng đúng chỗ, kiểm lối đi với người phụ trách rồi mới xác nhận hoàn tất công quả. // Ask the team to relocate the boxes, verify access with the coordinator, and then confirm completion.',
    'đã giúp người cao tuổi nhận đủ suất ăn, giữ lối đi thông và có ban công quả xác nhận // helped older visitors receive meals, kept access clear, and obtained committee confirmation',
    'xác nhận việc công quả đã hoàn thành // confirmation of completed community service')

_profile('police', 'Minh Quân | Thanh Hà | Đức Trung',
    'Anh Định · tổ trưởng cảnh sát khu vực // Định · neighborhood policing team leader',
    'hồ sơ có căn cứ, hòa giải đúng và bàn giao theo thẩm quyền // supported records, appropriate mediation, and handover within authority',
    'đối chiếu hồ sơ | lắng nghe các bên | ghi nhận bàn giao // file verification | hearing all parties | handover records',
    'Tổ nhận phản ánh mâu thuẫn khu phố; hai bên kể khác nhau và có tài liệu chưa được kiểm chứng. // The team receives a neighborhood dispute with conflicting accounts and unverified documents.',
    'Giao {a} đối chiếu tài liệu, {b} ghi nhận từng bên, {c} lập hồ sơ để chỉ huy xem xét theo thẩm quyền. // Have {a} verify documents, {b} record each side, and {c} prepare the file for authorized command review.',
    'Biên bản đã ghi kết luận nhưng thiếu lời trình bày của một bên và nguồn tài liệu. // The record contains a conclusion but lacks one party\'s statement and the document source.',
    'Yêu cầu bổ sung phần thiếu, ghi rõ điều chưa xác minh và chuyển chỉ huy kiểm theo đúng quyền hiện có. // Require the missing material, mark unverified facts clearly, and refer the file to command under existing authority.',
    'đã đối chiếu lời trình bày hai bên và bàn giao hồ sơ đủ căn cứ cho chỉ huy // checked both parties\' statements and handed a supported file to command',
    'nguồn tài liệu và lời trình bày hai bên // document sources and statements from both parties')

_profile('customs', 'Hữu Phước | Minh Thư | Gia Khang',
    'Chị Lam Thục · đội trưởng Đội Thủ tục // Lam Thục · head of the clearance team',
    'đúng luồng, đủ chứng từ và kết quả kiểm hóa có căn cứ // the right lane, complete documents, and supported inspection results',
    'đọc tờ khai | kiểm hóa thực tế | tính thuế // reading declarations | physical inspection | duty calculation',
    'Ca chiều có ba lô hàng: một luồng vàng thiếu C/O, một luồng đỏ chờ kiểm hóa và một tờ khai cần tính lại thuế. // The afternoon shift has three lots: a yellow-lane file missing a C/O, a red-lane lot awaiting inspection, and a declaration needing a duty recalculation.',
    'Giao {a} kiểm hồ sơ giấy, {b} kiểm hóa thực tế có biên bản, {c} tính thuế và đối chiếu chứng từ trước khi thông quan. // Have {a} check the paper file, {b} inspect the goods with a record, and {c} calculate duties and reconcile documents before clearance.',
    'Biên bản kiểm hóa ghi khớp nhưng số thùng đếm thực tế chưa được ký xác nhận. // The inspection record says the lot matches, but the physical carton count is not signed off.',
    'Đếm lại có người chứng kiến, sửa biên bản theo số thực tế và chuyển trưởng đội duyệt trước khi thông quan. // Recount with a witness, correct the record to the actual count, and send it to the team head before clearance.',
    'đã đối chiếu tờ khai, kiểm hóa và tính thuế đúng trước khi thông quan // reconciled the declaration, inspection, and duties before clearance',
    'số đếm thực tế có chữ ký và chứng từ thuế // a signed physical count and duty documents')

_profile('hotel', 'Quỳnh Như | Hữu Tâm | Minh Khoa',
    'Chị Hằng · trưởng ca lễ tân // Hằng · front desk shift lead',
    'phòng sạch đúng yêu cầu, thẻ đúng phòng và đồ thất lạc có sổ // clean rooms that match requests, the right key cards, and logged lost property',
    'lễ tân | buồng phòng | bảo trì // front desk | housekeeping | maintenance',
    'Sáng mùa lễ có ba việc: đoàn khách tới sớm, hai phòng vừa trả cần dọn và một phòng báo điều hòa chảy nước. // A holiday morning has three jobs: a group arriving early, two checked-out rooms to turn over, and a room reporting a leaking air conditioner.',
    'Giao {a} làm thủ tục và báo giờ có phòng thật, {b} dọn hai phòng theo đúng thứ tự, {c} ngắt điện rồi xử lý điều hòa và báo tình trạng phòng. // Have {a} handle check-in with honest room times, {b} turn over both rooms in order, and {c} isolate power, fix the air conditioner, and report the room status.',
    'Phòng được báo sẵn sàng nhưng vòi bồn rửa vẫn nhỏ giọt và hộ chiếu của khách trước còn trong ngăn kéo. // A room is reported ready, but the basin tap still drips and the previous guest\'s passport is still in a drawer.',
    'Khóa phòng chờ bảo trì, báo lễ tân gọi khách trước nhận lại hộ chiếu, ghi sổ đồ thất lạc rồi kiểm lại phòng. // Hold the room for maintenance, have the desk call the previous guest about the passport, log it, and reinspect the room.',
    'đã giao đúng phòng sạch, ghi sổ đồ thất lạc và khóa phòng hỏng trước khi bán // gave out only clean matching rooms, logged lost property, and held faulty rooms before selling them',
    'sổ bàn giao phòng và sổ đồ thất lạc // the room handover log and the lost property log')

_profile('banquet', 'Bảo Trân | Gia Huy | Thanh Tùng',
    'Chú Tâm · bếp trưởng nhà hàng tiệc // Tâm · banquet head chef',
    'bếp sạch từ đầu ca, món đúng lưu ý của bàn và sảnh tắt điện an toàn // a kitchen clean from the start of the shift, dishes that follow each table\'s notes, and a hall powered down safely',
    'sơ chế | nấu và ra món | bày trí sảnh // prep | cooking and the pass | hall setup',
    'Tối thứ bảy có hai tiệc: một đám cưới ba mươi bàn, một tiệc mừng thọ có bàn khách dị ứng hải sản, và sảnh còn chưa kiểm điện. // Saturday night has two parties: a thirty-table wedding, a longevity dinner with a table allergic to seafood, and a hall whose wiring has not been checked.',
    'Giao {a} sơ chế theo định lượng và thớt màu, {b} nấu và ra món theo thẻ dị ứng từng bàn, {c} kiểm điện, âm thanh rồi bày sảnh theo chủ đề. // Have {a} prep to the portion sheet with colour-coded boards, {b} cook and plate to each table\'s allergy cards, and {c} check the wiring and sound, then set the hall to the theme.',
    'Món đã lên quầy ra món nhưng nhiệt kế đo 48°C và khay của bàn dị ứng chưa có thẻ. // The dishes are at the pass, but the thermometer reads 48°C and the allergy table\'s tray has no card.',
    'Giữ khay lại, hâm món tới từ 75°C, dán thẻ dị ứng đúng bàn rồi đo lại trước khi ra món. // Hold the tray, reheat the food to at least 75°C, label the allergy table\'s tray, and measure again before it goes out.',
    'đã sát khuẩn đầu ca, ra món đúng nhiệt và đúng thẻ dị ứng, tắt điện cuối ca // sanitised at the start of the shift, served at the right temperature with the right allergy cards, and powered down at closing',
    'sổ vệ sinh đầu ca và phiếu kiểm quầy ra món // the opening hygiene log and the pass temperature sheet')

_profile('reception', 'Thu Hà | Minh Quân | Bảo Anh',
    'Chị Quyên · trưởng ca lễ tân Hoa Sứ // Quyên · Hoa Sứ front desk shift lead',
    'đúng phòng đúng người, đủ yêu cầu của khách và sổ giao ca không sót việc // the right room for the right party, every guest need met, and a handover log that misses nothing',
    'nhận khách | điều phối phòng | dịch vụ và phàn nàn // check-in | room coordination | services and complaints',
    'Chiều thứ sáu: một đoàn mười khách tới sớm, một bà cụ cần tầng trệt, ba phòng chưa dọn và hai chuyến xe sân bay sáng mai trùng giờ. // Friday afternoon: a party of ten arrives early, an elderly guest needs the ground floor, three rooms are not cleaned yet, and two airport rides tomorrow morning overlap.',
    'Giao {a} nhận đoàn theo bảng phòng và yêu cầu từng nhóm, {b} xếp lịch dọn phòng theo giờ khách tới, {c} xếp lịch xe và báo thức, ghi sổ giao ca. // Have {a} check the party in by the room board and each group\'s needs, {b} plan the cleaning by arrival time, and {c} schedule the rides and wake-up calls and write the handover.',
    'Hai phòng của một nhà đã giao nhưng không sát vách, còn sổ giao ca thiếu cuộc báo thức 5:30 khách đã nhờ. // The family\'s two rooms were given but are not side by side, and the handover log is missing the 5:30 wake-up call the guest asked for.',
    'Đổi sang hai phòng sát vách còn trống, đổi chìa, ghi lý do và thêm cuộc báo thức 5:30 vào sổ giao ca. // Move them to two free rooms side by side, swap the keys, note why, and add the 5:30 wake-up call to the handover log.',
    'đã xếp đúng phòng đủ yêu cầu, giao đúng chìa và ghi đủ việc còn dở vào sổ giao ca // put each party in a room that met every need, handed the right keys, and logged every pending job in the handover',
    'bảng phòng đã chốt và sổ giao ca // the final room board and the handover log')

_profile('teller', 'Thu Trang | Minh Đức | Ngọc Ánh',
    'Chị Hạnh · trưởng quầy giao dịch // Hạnh · teller counter lead',
    'đúng người, đúng tiền, quỹ khớp từng đồng và không lộ thông tin khách // the right person, the right money, a drawer that balances to the last note, and no customer data exposed',
    'đếm tiền và đổi cọc | đối chiếu người nhận | quỹ ATM và bàn giao // counting and bundling | recipient checks | ATM cash and handover',
    'Sáng ngày lương hưu có ba việc: các cụ xếp hàng từ sớm, dì Bảy cần đổi tiền lẻ gấp, và ATM trước cửa báo sắp hết tiền. // A pension-day morning has three jobs: retirees queuing early, dì Bảy needing small change fast, and the ATM outside running low.',
    'Giao {a} mở quầy đếm tiền chậm rãi cho các cụ, {b} đổi cọc cho dì Bảy và đối chiếu từng chuyển khoản, {c} cùng một người nữa tiếp quỹ ATM và ký sổ. // Have {a} open a counter and count slowly for the retirees, {b} bundle change for dì Bảy and check every transfer, and {c} refill the ATM with a second person and sign the log.',
    'Sổ bàn giao ghi đủ quỹ nhưng đếm thực tế hụt 200 nghìn và có một phiếu rút đã ký mà chưa chi. // The handover book says the drawer is full, but the count is 200k short and one signed withdrawal slip was never paid out.',
    'Chưa ký nhận: đối chiếu từng biên nhận, ghi khoản treo, lập biên bản với trưởng quầy rồi mới bàn giao. // Do not sign yet: match every receipt, log the pending item, and write a report with the counter lead before handing over.',
    'đã đếm hai lần trước mặt khách, chuyển đúng người nhận và bàn giao quỹ khớp sổ // counted twice in front of the customer, sent money to the right recipient, and handed over a drawer that matched the book',
    'biên nhận từng giao dịch và sổ bàn giao quỹ // a receipt for every transaction and the drawer handover book')

_profile('research', 'Minh Thư | Quốc Huy | Gia Bảo',
    'Cô Diệu Linh · viện trưởng Viện nghiên cứu Sông Mây // Diệu Linh · director of the Sông Mây research institute',
    'thí nghiệm có đối chứng, sổ ghi đủ cả lần hỏng và kết luận đúng mức dữ liệu // experiments with a control, a lab book that records the failures too, and conclusions the data supports',
    'lai tạo giống | thử công thức món | làm mẫu sáng chế // plant breeding | recipe trials | prototype building',
    'Hội đồng họp sáng thứ hai: một giống lúa chịu hạn chưa đủ lần lặp, ba công thức chè chờ nếm, và một mẫu quạt cầm tay vừa nứt ở bàn thả rơi. // The council meets on Monday morning: a drought-tolerant rice line short of repeats, three dessert recipes waiting to be tasted, and a handheld fan prototype that just cracked on the drop rig.',
    'Giao {a} làm thêm lần lặp có khay đối chứng, {b} mã hóa mẫu và chủ trì buổi nếm, {c} gia cố mẫu quạt rồi thử lại cả lô. // Have {a} run the extra repeats with a control tray, {b} code the samples and run the tasting, and {c} reinforce the fan and test a fresh batch.',
    'Biểu đồ đã in cho hội đồng nhưng có hai ô ruộng ngập nước vẫn được tính vào trung bình, và sổ thí nghiệm thiếu chữ ký ngày thứ ba. // The chart is printed for the council, but two flooded plots are still counted in the mean, and the lab book is missing the third day\'s signature.',
    'Giữ biểu đồ lại, bỏ hai ô ngập có ghi lý do, tính lại trung bình và xin chữ ký bổ sung có ghi chú ngày sửa. // Hold the chart, drop the two flooded plots with the reason written down, recompute the mean, and get the missing signature with a dated correction note.',
    'đã giữ số liệu thật, có đối chứng, ghi đủ mẫu hỏng và trình hội đồng đúng mức kết quả // kept the real numbers, used a control, logged every spoiled sample, and presented the council only what the results show',
    'sổ thí nghiệm đánh số trang và biên bản hội đồng // the page-numbered lab book and the council minutes')

_profile('radio', 'Thu Trang | Quang Vinh | Bích Ngọc',
    'Chị Hoa · trưởng đài phát thanh phường // Hoa · ward radio station head',
    'tin đọc đúng thứ tự, chỉ đọc bản quảng cáo đã duyệt và không để sóng câm khi mất điện // bulletins read in the right order, only approved ad scripts on air, and no dead air in a power cut',
    'đọc bản tin | dựng chương trình ca nhạc | kỹ thuật phòng máy // reading bulletins | building music shows | studio engineering',
    'Sáng thứ hai có cảnh báo mưa bão, nhà tài trợ gửi kịch bản mới lúc chín giờ năm mươi chín, và máy phát dự phòng chưa ai thử từ tuần trước. // Monday morning brings a storm warning, a sponsor sends a new script at 9:59, and nobody has tested the backup generator since last week.',
    'Giao {a} đọc bản tin theo thứ tự tin khẩn trước, {b} chỉ dựng quảng cáo theo bản đã ký duyệt, {c} thử máy phát và bộ lưu điện trước giờ lên sóng. // Have {a} read the bulletin urgent items first, {b} build the ad only from the signed script, and {c} test the generator and the UPS before air time.',
    'Spot quảng cáo đã lên lịch nhưng là bản gửi qua tin nhắn chưa ai duyệt, còn câu “dùng là khỏi bệnh”. // The ad spot is scheduled, but it is the unapproved version sent by text and still says “cures any illness”.',
    'Rút spot khỏi lịch, đọc bản đã ký duyệt gần nhất, gạch câu phóng đại và báo nhà tài trợ trước khung quảng cáo. // Pull the spot, read the latest signed script, strike the exaggerated claim, and tell the sponsor before the ad break.',
    'đã đọc tin khẩn trước, chỉ phát quảng cáo đã duyệt và xử lý mất điện theo sổ sự cố // read urgent items first, aired only approved ads, and handled the power cut by the incident log',
    'sổ duyệt kịch bản và sổ sự cố kỹ thuật // the script approval log and the technical incident log')

_profile('moto', 'Văn Tài | Minh Khôi | Ngọc Hân',
    'Út Lanh · chủ tiệm sửa xe đầu hẻm // Út Lanh · owner of the alley motorbike shop',
    'chốt đúng bệnh xe, làm theo sổ tay và giao đúng xe đúng biển // the right fault named, the notebook followed, and the right bike handed back by its plate',
    'chẩn đoán máy | bảo dưỡng định kỳ | điện và phanh // engine diagnosis | routine servicing | electrics and brakes',
    'Chiều mưa ngập, năm chiếc xe chết máy xếp hàng, một khách đòi đề thử ngay và thùng phụ tùng giá rẻ không hóa đơn vừa chở tới. // A flooded afternoon: five stalled bikes queue up, one customer wants the engine cranked at once, and a box of cheap parts with no invoice has just arrived.',
    'Giao {a} phát số và dặn không ai đề xe, {b} xả nước buồng đốt và nhớt theo sổ tay, {c} kiểm nguồn phụ tùng trước khi nhận. // Have {a} hand out numbers and tell everyone not to crank, {b} clear the cylinder and the oil by the notebook, and {c} check where the parts come from before taking any.',
    'Một chiếc xe ngập đã được đề thử ba lần trước khi tháo bugi, nhớt trắng đục vẫn trong máy. // One flooded bike was cranked three times before its plug came out, and the milky oil is still in the engine.',
    'Dừng đề, tháo bugi, đẩy nước ra, súc nhớt hai lần, ghi phiếu thật cho khách và báo chủ tiệm. // Stop cranking, pull the plug, push the water out, flush the oil twice, write the real story on the slip, and tell the owner.',
    'đã không đề xe ngập, súc đủ nhớt, từ chối phụ tùng không rõ nguồn và giao đúng xe // cranked no flooded bike, flushed the oil fully, refused untraceable parts, and handed back the right bikes',
    'phiếu sửa xe ghi số km và túi đồ cũ trả khách // the repair slip with the odometer reading and the bag of old parts returned')

_profile('vet', 'Hồng Nhung | Đức Anh | Phương Vy',
    'Bác sĩ Thảo · trưởng phòng khám thú y // Dr Thảo · head of the vet clinic',
    'cân trước khi cho thuốc, ca cấp cứu ưu tiên và nói thật với chủ nuôi // weighing before dosing, emergencies first, and honesty with owners',
    'tiêm phòng | cấp cứu ngộ độc | phẫu thuật nhỏ // vaccinations | poisoning emergencies | minor surgery',
    'Sáng thứ bảy phòng chờ đông, một cún nôn ra máu chưa tiêm phòng, một mèo đực rặn tiểu không ra, và tủ vắc xin vừa cúp điện đêm qua. // Saturday morning: a full waiting room, an unvaccinated puppy vomiting blood, a tom cat that cannot pee, and the vaccine fridge lost power overnight.',
    'Giao {a} đưa cún vào phòng cách ly và sát trùng phòng chờ, {b} xử lý ngay ca tắc tiểu, {c} kiểm nhiệt độ tủ và loại vắc xin mất lạnh. // Have {a} take the puppy to isolation and disinfect the waiting room, {b} handle the blocked cat at once, and {c} check the fridge log and discard any vaccine that warmed up.',
    'Liều thuốc gây nôn trong phiếu tính theo cân ước chừng, không có số cân thật. // The dose on the slip was worked out from a guessed weight, with no real reading from the scale.',
    'Cân lại bé, tính lại liều theo sổ tay, ghi số cân vào phiếu và báo bác sĩ trưởng trước khi cho thuốc. // Weigh the dog again, redo the dose by the notebook, write the weight on the slip, and tell the head vet before giving anything.',
    'đã cách ly đúng lúc, tính liều theo cân thật và loại vắc xin mất lạnh // isolated in time, dosed by real weights, and discarded the warmed vaccines',
    'phiếu khám ghi số cân và sổ nhiệt độ tủ vắc xin // the case slip with the weight and the vaccine fridge temperature log')

_profile('tuning', 'Trọng Nghĩa | Gia Bảo | Khánh Linh',
    'Anh Tư Pít-tông · chủ xưởng độ xe // Tư Pít-tông · owner of the tuning shop',
    'độ đúng mục tiêu trong ngân sách, đúng luật và đo thật trên dyno // builds that fit the goal and the budget, stay legal, and are measured honestly on the dyno',
    'map ECU và dyno | phanh và gầm | đo ồn và khí thải // ECU maps and the dyno | brakes and chassis | noise and emission checks',
    'Sáng thứ bảy trước ngày đua đèo, bốn xe chờ lên băng dyno, một khách đòi lắp pô thẳng cho kịp giờ và thùng turbo giá rẻ không hóa đơn vừa chở tới. // The Saturday before a hill-climb day: four cars wait for the dyno, one customer wants a straight pipe fitted in time, and a box of cheap turbos with no invoice has just arrived.',
    'Giao {a} chạy dyno và đọc AFR từng xe, {b} kiểm phanh, ốc bánh và rò rỉ trước khi chạy thử, {c} đo tiếng ồn, khí thải và từ chối đồ không rõ nguồn. // Have {a} run the dyno and read each AFR, {b} check brakes, wheel nuts and leaks before any test drive, and {c} measure noise and emissions and refuse untraceable parts.',
    'Một xe đua đèo đã nạp map mới nhưng AFR ở tải lớn đọc 14,1, phiếu vẫn ghi “đạt”. // One hill-climb car has a new map but reads AFR 14.1 at full load, and the slip still says “passed”.',
    'Dừng giao xe, nạp lại map, đọc lại AFR trên dyno, ghi đúng số vào thẻ thông số và báo chủ xưởng. // Hold the handover, reflash the map, read the AFR again on the dyno, write the true figure on the spec card, and tell the owner.',
    'đã đọc lại AFR từng xe, từ chối pô thẳng và turbo không rõ nguồn, chạy thử đủ trước khi giao // re-read every AFR, refused the straight pipe and the untraceable turbos, and test-drove every car before handover',
    'sổ dyno ghi trước và sau độ cùng thẻ thông số có số đo ồn và khí thải // the dyno log with before and after figures and the spec card with noise and emission readings')

_profile('kol', 'Bảo Ngọc | Gia Huy | Thanh Trúc',
    'Chị Ngân · chủ Studio Hẻm Xanh // Ngân · owner of the Hẻm Xanh studio',
    'ghi rõ quảng cáo, quay đúng brief và báo cáo số thật // clear ad labels, footage true to the brief, and honest numbers',
    'quay và ánh sáng | dựng và nhạc miễn phí bản quyền | trả lời bình luận // filming and light | editing with royalty-free music | answering comments',
    'Ba nhãn hàng cùng hẹn đăng tối nay, một nhãn đòi bỏ chữ quảng cáo, một video dùng nhạc hit chưa xin phép và một trang giả mạo kênh đang nhắn người xem chuyển tiền. // Three brands want their posts out tonight; one wants the ad label dropped, one video uses an unlicensed hit, and a fake page is messaging viewers for money.',
    'Giao {a} quay lại cảnh thiếu sáng, {b} thay nhạc bằng bản trong thư viện miễn phí bản quyền, {c} ghim cảnh báo trang giả và trả lời người xem. // Have {a} reshoot the dim scene, {b} swap the music for a track from the royalty-free library, and {c} pin a warning about the fake page and answer viewers.',
    'Báo cáo gửi nhãn hàng ghi lượt xem đã cộng thêm lượt mua, không ghi rõ nguồn số liệu. // The report to the brand counts bought views in its total and does not say where the numbers came from.',
    'Bỏ lượt mua khỏi báo cáo, ghi số thật từ trang thống kê, đính kèm đường dẫn video và báo nhãn hàng. // Remove the bought views, write the real figures from the analytics page, attach the video link, and tell the brand.',
    'đã ghi rõ quảng cáo, thay nhạc không phép và báo cáo đúng số thật // labelled every ad, replaced the unlicensed music, and reported the real numbers',
    'báo cáo số liệu có đường dẫn video và mã hợp đồng // the numbers report with the video link and the contract code')

_profile('singer', 'Thu Hà | Quang Vinh | Mỹ Linh',
    'Cô Diệu Hiền · chủ Phòng trà Mây Chiều // Diệu Hiền · owner of the Mây Chiều tea room',
    'hát thật, chỉ hát bài đã xin phép và giữ đúng giờ lượt hát // live singing, only licensed songs, and every turn on time',
    'thanh nhạc | âm thanh sân khấu | giao lưu khán giả // voice | stage sound | talking with the audience',
    'Tối thứ bảy kín bàn, ca sĩ khách mời khàn tiếng xin hát nhép, micro không dây sắp hết pin và một bàn đòi hát năm bài liền. // A full Saturday night: the guest singer has lost her voice and wants to mime, the wireless mic is nearly flat, and one table demands five songs in a row.',
    'Giao {a} hát mộc bài nhẹ thay ca sĩ khách, {b} thay pin và để sẵn micro dây, {c} giữ thứ tự giấy xin bài cho cả phòng. // Have {a} sing a soft song unplugged in the guest\'s place, {b} change the batteries and set out a wired mic, and {c} keep the request slips in order for the whole room.',
    'Một lượt hát kéo dài quá giờ mười phút, ca sĩ sau phải cắt bớt bài. // One turn ran ten minutes over, and the next singer had to drop a song.',
    'Ghi lại giờ từng bài, hát điệp khúc ngắn khi khán giả xin thêm và báo chủ phòng trà trước khi kéo dài. // Time every song, sing a short chorus when the room asks for more, and ask the owner before running over.',
    'đã không hát nhép, giữ đúng giờ và chỉ hát bài trong sổ hợp âm // no miming, every turn on time, and only songs from the licensed songbook',
    'sổ lượt hát ghi giờ từng bài và giấy xin bài đã đọc // the turn log with each song\'s time and the request slips read out')

_profile('actor', 'Hoài An | Trọng Nhân | Kim Ngân',
    'Đạo diễn Minh Triết · Hãng phim Bến Mây // Director Minh Triết · Bến Mây studio',
    'thuộc thoại, đứng đúng dấu và an toàn trước khi đẹp // lines learned, marks hit, and safety before beauty',
    'diễn xuất | hành động an toàn | nối cảnh // acting | safe stunts | continuity',
    'Ngày quay dày: cảnh giằng co chưa tập với điều phối hành động, diễn viên nhí đã quay quá giờ và trang kịch bản tập cuối vừa bị chụp lén. // A heavy shooting day: the struggle scene has not been rehearsed with the stunt coordinator, the child actor is past her hours, and a page of the final script has been photographed.',
    'Giao {a} tập chậm cảnh giằng co với điều phối, {b} cho bé nghỉ và dời cảnh của bé sang mai, {c} báo thư ký trường quay cất kịch bản và xóa ảnh. // Have {a} rehearse the struggle slowly with the coordinator, {b} send the child home and move her scene to tomorrow, and {c} get the script supervisor to lock up the script and have the photo deleted.',
    'Ảnh nối cảnh cho thấy ly trà ở tay phải, nhưng lượt vừa quay diễn viên cầm tay trái. // The continuity photo shows the cup in the right hand, but in the last take the actor held it in the left.',
    'Đối chiếu sổ ảnh nối cảnh, quay lại lượt đó với ly ở tay phải và ghi chú cho bên dựng. // Check the continuity book, reshoot that take with the cup in the right hand, and leave a note for the editors.',
    'đã tập an toàn trước khi quay, giữ giờ cho diễn viên nhí và giữ kín kịch bản // rehearsed safely before rolling, kept the child actor\'s hours, and kept the script secret',
    'sổ ảnh nối cảnh và bảng lượt quay đạt // the continuity book and the good-takes sheet')

_profile('jewelry', 'Kim Ngân | Bảo Châu | Minh Trí',
    'Cô Ba Ngọc · chủ tiệm vàng Ngọc Mây // Ba Ngọc · owner of the Ngọc Mây gold shop',
    'cân trước mặt khách, đúng tuổi vàng, giá theo bảng hôm nay và không mua đồ không rõ nguồn gốc // weighing in front of the customer, the right purity, today\'s board, and nothing of unknown origin bought',
    'cân và tính tiền vàng | kiểm định kim cương | mua lại vàng cũ // weighing and pricing gold | appraising diamonds | buying old gold back',
    'Sáng rằm tháng Giêng, khách xếp hàng mua vàng lấy may, máy quét tuổi vàng báo lỗi và một người lạ mang túi nhẫn cưới tới bán gấp. // The full-moon morning of the first lunar month: a queue for lucky gold, the purity scanner throws an error, and a stranger brings a bag of wedding rings to sell fast.',
    'Giao {a} phát số và bán đúng bảng niêm yết, {b} thử tuổi vàng bằng đá thử khi máy hỏng, {c} xem giấy tờ người bán và ghi sổ mua hàng. // Have {a} hand out numbers and sell at the posted board, {b} test purity on the touchstone while the scanner is down, and {c} check the seller\'s papers and keep the purchase ledger.',
    'Một chiếc nhẫn mua lại được ghi tuổi 14K dù máy quét báo 18K, khách đã ký sổ. // A bought-back ring was written down as 14K though the scanner said 18K, and the customer has signed the ledger.',
    'Gọi khách quay lại, ghi đúng 18K, trả thêm phần chênh, ghi chú ngày sửa vào sổ và báo chủ tiệm. // Call the customer back, write 18K, pay the difference, note the correction date in the ledger, and tell the owner.',
    'đã bán đúng giá niêm yết, thử tuổi vàng đúng cách và từ chối đồ không rõ nguồn gốc // sold at the posted board, tested purity properly, and refused goods of unknown origin',
    'sổ mua hàng có CCCD người bán và hóa đơn từng món // the purchase ledger with sellers\' IDs and an invoice for every piece')

_profile('car_dealer', 'Hoàng Long | Thanh Hà | Gia Huy',
    'Anh Quân · chủ đại lý xe Phố Mây // Quân · owner of the Phố Mây dealership',
    'xe đúng nhu cầu khách, thông số theo hãng, đủ giấy tờ và không tự cho nợ // the right vehicle for each customer, the maker\'s specs, complete papers, and no in-house credit',
    'tư vấn bán xe | kiểm xe mới | hồ sơ đăng ký // sales advice | new-vehicle checks | registration papers',
    'Cuối tháng có chương trình khuyến mãi, mười khách tới cùng lúc, một lô xe mới chưa kiểm và bộ hồ sơ đăng ký của ba khách còn thiếu chữ ký. // A month-end promotion brings ten customers at once, a new batch is still unchecked, and three customers\' registration files are missing signatures.',
    'Giao {a} tư vấn theo nhu cầu từng khách, {b} kiểm năm bước lô xe mới trước khi trưng bày, {c} gọi khách ký bổ sung hồ sơ. // Have {a} advise each customer by their needs, {b} run the five-step check on the new batch before display, and {c} call customers to sign their files.',
    'Một chiếc xe đã giao cho khách với biển tạm của xe khác vì hồ sơ chưa xong. // A vehicle was handed over with another vehicle\'s temporary plate because its papers were not done.',
    'Gọi khách đổi lại biển, giữ xe ở đại lý tới khi có biển đúng, xin lỗi khách và ghi sổ hồ sơ chờ. // Call the customer to swap the plate back, keep the vehicle at the dealer until its own plate comes, apologise, and log it in the pending-papers book.',
    'đã tư vấn đúng nhu cầu, kiểm đủ xe mới và giao xe khi hồ sơ đủ // advised by real needs, checked every new vehicle, and handed over only with complete papers',
    'biên bản giao xe có số khung và sổ hồ sơ chờ bổ sung // the hand-over record with the frame number and the pending-papers book')

_profile('drain', 'Hoàng Hải | Quốc Dũng | Thảo Chi',
    'Trưởng đội thoát nước // Drainage team supervisor',
    'nhận diện nguy cơ, xử lý đúng phạm vi và nghiệm thu dòng chảy // hazard recognition, work within scope, and verified drainage',
    'đánh giá điểm tắc | kiểm trang bị | ghi nhận nghiệm thu // blockage assessment | equipment checks | acceptance records',
    'Điểm tắc gần khu đông người, có mùi bất thường; người mới định tự vào kiểm cho nhanh. // A blockage near a busy area has an unusual smell; a newcomer wants to enter alone to inspect it quickly.',
    'Giao {a} đánh giá từ vị trí an toàn, {b} kiểm điều kiện và trang bị, {c} liên hệ đội có thẩm quyền nếu vượt phạm vi. // Have {a} assess from a safe position, {b} check conditions and equipment, and {c} contact the authorized team if the job exceeds scope.',
    'Nước đã rút một phần nhưng khu làm việc chưa được kiểm sạch và chưa có kết quả thử lại. // Water has partly drained, but the work area is not checked clean and no retest is recorded.',
    'Giữ nghiệm thu chờ kiểm, cho đội đủ điều kiện thử lại và làm sạch khu vực rồi ghi kết quả thực. // Withhold acceptance, have the qualified team retest and clean the area, and document actual results.',
    'đã nhận diện nguy cơ, chuyển đúng đội và có kết quả nghiệm thu dòng chảy // recognized a hazard, referred it to the right team, and obtained verified drainage results',
    'đánh giá nguy cơ và kết quả nghiệm thu // hazard assessments and acceptance results')

_profile('homemaker', 'Thu Thảo | Minh Hiếu | Ngọc Trâm',
    'Chị Thảo · gia đình sử dụng dịch vụ // Thảo · client household',
    'đủ việc đã nhận, tiết kiệm hợp lý và tôn trọng nếp nhà // completing agreed tasks, reasonable savings, and respecting household routines',
    'lập lịch việc nhà | quản lý đồ dùng | trao đổi nhu cầu gia đình // household scheduling | supplies management | family-needs communication',
    'Gia đình đổi giờ ăn và có người cần yên tĩnh nghỉ; lịch dọn nhà đang trùng giờ nghỉ. // The family changes mealtime and someone needs quiet rest; cleaning is scheduled during that rest period.',
    'Giao {a} đổi thứ tự việc, {b} chuẩn bị đủ đồ không lãng phí, {c} xác nhận lại giờ với gia đình trước thực hiện. // Have {a} reorder tasks, {b} prepare supplies without waste, and {c} reconfirm timing with the household.',
    'Nhà trông gọn nhưng ngăn tủ gia đình dặn không mở đã bị xếp lại. // The house looks tidy, but a cupboard marked private has been reorganized.',
    'Báo trung thực với gia đình, ghi nhận phạm vi đã vượt và thống nhất khắc phục; kiểm lại danh mục được phép. // Tell the household honestly, record the scope breach, agree on a remedy, and recheck permitted tasks.',
    'đã điều chỉnh lịch đúng nếp nhà và có gia đình xác nhận đủ việc đã nhận // adjusted the schedule to household routines and obtained confirmation of completed agreed tasks',
    'xác nhận phạm vi việc gia đình đã đồng ý // confirmation of the household-approved scope')

_profile('ice_cream', 'Hạnh Nguyên | Nhật Quang | Diệu My',
    'Cô Hiền · chủ tiệm kem // Hiền · ice cream shop owner',
    'bảo quản lạnh, đúng món và dụng cụ sạch // cold storage, correct orders, and clean tools',
    'kiểm bảo quản | chia phần | ghép đơn sự kiện // storage checks | portioning | event-order assembly',
    'Đơn sự kiện cần nhiều vị kem; thùng vận chuyển vừa được chuyển sang chỗ nóng hơn. // An event order needs several flavors; the transport box has just been moved to a warmer location.',
    'Giao {a} kiểm điều kiện lạnh, {b} chia phần theo phiếu, {c} ghép nhãn vị và kiểm lại trước xuất. // Have {a} check cold conditions, {b} portion by ticket, and {c} match flavor labels and verify before dispatch.',
    'Một khay kem mềm bất thường nhưng vẫn được xếp vào đơn vì còn đúng số phần. // One tray is unusually soft but was included because the portion count is correct.',
    'Tách khay chờ đánh giá theo quy trình bảo quản, thay phần đủ điều kiện và kiểm lại đơn trước giao. // Isolate the tray for storage assessment, replace it with suitable portions, and recheck before delivery.',
    'đã phát hiện khay không đạt bảo quản và giao đủ phần được kiểm đúng vị // identified a storage failure and delivered verified portions with correct flavors',
    'kiểm bảo quản lạnh // cold-storage checks')

_profile('nail', 'Hải Yến | Phương Nhi | Mai Anh',
    'Chị Diệp · chủ tiệm nail // Diệp · nail salon owner',
    'mẫu đã thống nhất, dụng cụ sạch và chăm sóc đúng phạm vi // agreed designs, clean tools, and care within scope',
    'tư vấn mẫu móng | chuẩn bị dụng cụ | kiểm hoàn thiện mẫu // nail-design consultation | tool preparation | final design checks',
    'Khách chọn mẫu nhiều bước, người mới chưa quen dụng cụ và lịch hẹn kế tiếp sát giờ. // A customer chose a multistep design; a newcomer is unfamiliar with the tools and the next appointment is close.',
    'Giao {a} chốt mẫu và thời gian thật, {b} kiểm dụng cụ, {c} kèm người mới ở bước phù hợp và kiểm trước bàn giao. // Have {a} agree on the design and realistic time, {b} check tools, and {c} supervise suitable beginner steps and verify the result.',
    'Mẫu đúng màu nhưng bộ dụng cụ đã dùng chưa có xác nhận xử lý vệ sinh. // The design has the correct colors, but the used tool set lacks a hygiene-processing record.',
    'Dừng dùng bộ dụng cụ, báo người phụ trách xử lý theo quy trình và kiểm điều kiện trước tiếp khách. // Stop using the set, notify the supervisor for procedural processing, and verify conditions before further service.',
    'đã giữ đúng mẫu được duyệt và kiểm dụng cụ đầy đủ trước phục vụ // followed the approved design and completed tool checks before service',
    'xác nhận xử lý vệ sinh dụng cụ // tool hygiene-processing confirmation')

_profile('pho', 'Thanh Tâm | Hữu Lộc | Ngọc Dung',
    'Bác Lâm · chủ quán phở // Lâm · pho restaurant owner',
    'đúng tô, nước dùng đạt và phục vụ sạch // correct bowls, acceptable broth, and hygienic service',
    'kiểm nước dùng | đọc phiếu tô | phối hợp ra món // broth checks | bowl-ticket reading | service coordination',
    'Đoàn khách gọi nhiều loại tô, một đơn có yêu cầu riêng và nồi nước dùng mới chưa kiểm. // A group orders several bowl types with one special request, while a new broth pot awaits checks.',
    'Giao {a} kiểm nồi mới, {b} tách phiếu yêu cầu riêng, {c} ghép đúng tô theo bàn rồi kiểm cùng bếp. // Have {a} check the new pot, {b} separate the special ticket, and {c} match bowls to tables with a kitchen cross-check.',
    'Tô đã lên khay nhưng phần yêu cầu bỏ nguyên liệu vẫn có nguyên liệu đó. // A bowl is on the tray despite containing an ingredient the customer asked to omit.',
    'Giữ tô chưa phục vụ, xác minh yêu cầu và làm lại theo khả năng bếp; kiểm đúng phiếu trước ra bàn. // Hold the bowl, verify the request, remake it within kitchen capability, and check the ticket before serving.',
    'đã bắt đúng lỗi yêu cầu riêng trước ra món và lưu xác nhận của bếp // caught a special-request error before service and recorded kitchen confirmation',
    'kiểm nước dùng và phiếu tô // broth and bowl-ticket checks')

_profile('com', 'Thùy Trang | Công Minh | Ngọc Quyên',
    'Dì Bảy · chủ quán cơm // Bảy · rice-meal shop owner',
    'suất đủ, món đạt và giữ điều kiện phục vụ phù hợp // complete portions, acceptable dishes, and suitable serving conditions',
    'kiểm món chín | chia suất | tổ chức giao cơm // cooked-dish checks | meal portioning | meal delivery organization',
    'Đơn suất ăn đông người có hai thực đơn; người mới định chia trước món còn chờ kiểm. // A large meal order has two menus; a newcomer wants to portion a dish before its check is complete.',
    'Giao {a} kiểm món đủ điều kiện, {b} chia theo thực đơn đã duyệt, {c} kiểm số suất và giờ giao. // Have {a} verify dish suitability, {b} portion approved menus, and {c} check meal counts and delivery times.',
    'Thùng cơm đủ hộp nhưng một nhóm thiếu món và thời điểm đóng hộp chưa được ghi. // The crate contains enough boxes, but one group lacks a dish and packing times are unrecorded.',
    'Kiểm lại từng nhóm thực đơn và điều kiện bảo quản, bổ sung đúng phần rồi ghi và xác minh trước giao. // Recheck menu groups and storage conditions, complete the portions, and document and verify before delivery.',
    'đã giữ đủ món từng suất và đối chiếu điều kiện giao được bên nhận xác nhận // completed every meal and verified delivery conditions with the recipient',
    'kiểm thành phần suất và điều kiện giữ món // portion-content and food-holding checks')

_profile('photobooth', 'Quỳnh Mai | Hoàng Phúc | Gia Linh',
    'Chị Lam · chủ tiệm Tách Tách // Lam · Tách Tách studio owner',
    'bố cục đúng, ảnh được đồng ý sử dụng và bàn giao đủ // correct composition, consent for image use, and complete delivery',
    'bố trí khung ảnh | hỗ trợ khách chụp | kiểm file bàn giao // frame composition | guest posing support | delivery-file checks',
    'Sự kiện có khách đồng ý chụp nhưng không đồng ý đăng ảnh; người mới đang gom ảnh để quảng bá. // Event guests consent to being photographed but not to publication; a newcomer is collecting promotional images.',
    'Giao {a} chuẩn bị mẫu khung, {b} xác nhận lựa chọn của khách, {c} tách file theo quyền sử dụng và kiểm trước giao. // Have {a} prepare frames, {b} confirm guest preferences, and {c} separate files by usage consent and verify delivery.',
    'Gói ảnh đủ số nhưng chứa ảnh của nhóm khác và một file chưa có đồng ý đăng. // The package has enough images but includes another group\'s photo and a file without publication consent.',
    'Giữ gói ảnh, đối chiếu nhóm và quyền sử dụng, xuất lại đúng file rồi kiểm cùng phiếu bàn giao. // Hold the package, reconcile group ownership and consent, export the correct files, and check the delivery sheet.',
    'đã tách đúng ảnh riêng tư và giao đủ file đúng nhóm, đúng lựa chọn của khách // separated private images and delivered complete files to the correct group under their preferences',
    'xác nhận quyền sử dụng và mã nhóm ảnh // usage-consent and photo-group confirmation')

_profile('giupviec', 'Ngọc Oanh | Thanh Hằng | Đức Phúc',
    'Cô Mai · tổ trưởng Nhà Thơm // Mai · Nhà Thơm cleaning team leader',
    'đúng hạng mục, tài sản nguyên vẹn và bàn giao rõ // agreed cleaning scope, intact property, and clear handover',
    'đọc danh mục nhà | chọn vật dụng phù hợp | kiểm bàn giao phòng // household checklist review | choosing suitable supplies | room handover checks',
    'Tổ có hai nhà liên tiếp, một nhà có sàn cần cách chăm riêng và chủ chưa đồng ý dọn tủ cá nhân. // The team has two consecutive homes; one has flooring needing special care and no consent to clean a private cupboard.',
    'Giao {a} xác nhận phạm vi, {b} chọn vật dụng theo bề mặt, {c} kiểm từng phòng và hẹn bàn giao thực tế. // Have {a} confirm scope, {b} choose supplies for each surface, and {c} check rooms and agree on a realistic handover.',
    'Phòng đã sạch nhưng một vật trang trí bị nứt, chưa có ghi nhận tình trạng ban đầu. // The room is clean, but an ornament is cracked and no initial-condition record exists.',
    'Báo trung thực, đối chiếu hình và ghi nhận với gia đình; xử lý theo quy trình trước chốt bàn giao. // Report honestly, compare photos and record the issue with the household, then follow procedure before closing handover.',
    'đã bảo vệ đúng bề mặt và bàn giao đủ hạng mục có gia đình xác nhận // protected surfaces correctly and handed over all agreed tasks with household confirmation',
    'ghi nhận tình trạng tài sản // property-condition records')

_profile('naucom', 'Thảo Nhi | Minh Đức | Ngọc Tuyết',
    'Cô Hạnh · điều phối bếp nhà // Hạnh · home-cooking coordinator',
    'khẩu phần phù hợp, đủ món và an toàn bữa ăn // suitable portions, complete menus, and meal safety',
    'đọc thực đơn gia đình | chuẩn bị nguyên liệu | sắp giờ nấu // household-menu review | ingredient preparation | cooking schedules',
    'Bữa nhà có người ăn theo yêu cầu riêng; khách tăng số người nhưng không muốn đổi giờ ăn. // A household meal includes a special dietary request; the guest count rises without changing mealtime.',
    'Giao {a} xác nhận thực đơn và khả năng đáp ứng, {b} kiểm nguyên liệu, {c} sắp lịch món và báo sớm phần cần đổi. // Have {a} confirm the menu and feasibility, {b} check ingredients, and {c} schedule dishes and flag necessary changes early.',
    'Bàn đủ món nhưng phần dành riêng không được đánh dấu, khó biết có đúng nguyên liệu đã thống nhất. // All dishes are present, but the special portion is unmarked and its agreed ingredients cannot be verified.',
    'Giữ phần chưa chắc, xác minh nguyên liệu và chuẩn bị lại nếu cần; kiểm nhãn phần riêng trước phục vụ. // Hold the uncertain portion, verify ingredients and remake if necessary, then check its label before service.',
    'đã chuẩn bị đúng phần riêng và đủ món đúng giờ được gia đình xác nhận // prepared the special portion correctly and served the complete meal on time with household confirmation',
    'đối chiếu nguyên liệu phần riêng // special-portion ingredient checks')

_profile('babysitter', 'Mai Lan | Thu Ngân | Khánh Vân',
    'Cô Tâm · tổ trông trẻ Mèo Con // Tâm · Mèo Con childcare team leader',
    'giám sát an toàn, đúng nếp sinh hoạt và giao nhận có xác nhận // safe supervision, agreed routines, and confirmed handovers',
    'đọc hướng dẫn gia đình | tổ chức hoạt động phù hợp | ghi nhận giao nhận // family-instruction review | suitable activity planning | handover records',
    'Hai trẻ có giờ nghỉ khác nhau; người mới muốn đưa cả hai đi cùng trong khi chưa thống nhất người giám sát. // Two children have different rest times; a newcomer wants to take both out without an agreed supervisor.',
    'Giao {a} kiểm hướng dẫn gia đình, {b} chia hoạt động trong phạm vi giám sát, {c} giữ bàn giao rõ từng trẻ với người đủ trách nhiệm. // Have {a} review family instructions, {b} organize activities within supervision limits, and {c} maintain explicit handovers for each child to a responsible caregiver.',
    'Sổ ghi đã giao trẻ nhưng người tới đón chưa được đối chiếu với danh sách gia đình xác nhận. // The log marks a child as collected, but the arriving adult has not been checked against the family-approved list.',
    'Giữ trẻ trong giám sát, xác minh người đón qua kênh đã thống nhất và chỉ ghi bàn giao sau xác nhận. // Keep the child supervised, verify the collector through the agreed channel, and record handover only after confirmation.',
    'đã giữ giám sát liên tục và xác minh đúng người đón theo hướng dẫn gia đình // maintained continuous supervision and verified the collector under family instructions',
    'xác nhận người đón và bàn giao trẻ // collector verification and child handover records')

_profile('library', 'Quỳnh Hoa | Thanh Nam | Minh Uyên',
    'Cô Nguyệt · phụ trách thư viện // Nguyệt · library supervisor',
    'mượn trả chính xác, tìm sách phù hợp và giữ hồ sơ // accurate loans and returns, suitable book guidance, and preserved records',
    'tra cứu sách | kiểm mã lưu trữ | tổ chức buổi đọc // book searches | archive-code checks | reading-session organization',
    'Buổi đọc cộng đồng trùng lượt trả sách; một tài liệu lưu trữ cần điều kiện sử dụng riêng. // A community reading event overlaps with returns, and one archival item has special access conditions.',
    'Giao {a} tìm sách theo nhu cầu, {b} xử lý mã mượn trả và điều kiện tài liệu, {c} giữ buổi đọc đúng lịch. // Have {a} find suitable books, {b} handle circulation codes and archive conditions, and {c} keep the reading session on schedule.',
    'Sổ ghi đã trả nhưng mã bản sách trên kệ khác bản bạn đọc mượn. // The system marks an item returned, but the copy on the shelf has a different code from the borrowed copy.',
    'Đối chiếu mã bản thực với phiếu mượn, xác minh cùng bạn đọc và sửa hồ sơ có dấu vết trước chốt. // Compare the physical copy code with the loan slip, verify with the reader, and retain a correction trail before closure.',
    'đã tìm đúng bản sách thất lạc và cập nhật mượn trả có đối chiếu // found the missing copy and reconciled its circulation record',
    'đối chiếu mã bản và phiếu mượn // copy-code and loan-slip reconciliation')

_profile('pilot', 'Quốc Anh | Minh Khôi | Bảo Châu',
    'Cơ trưởng Vân · giám sát huấn luyện // Captain Vân · training supervisor',
    'tuân thủ quy trình bay và quyết định trong quyền được giao // following flight procedures and decisions within assigned authority',
    'rà hồ sơ chuyến | phối hợp tổ lái | ghi nhận huấn luyện // flight-document review | crew coordination | training records',
    'Trong buổi mô phỏng, thông tin chuyến vừa thay đổi; học viên muốn bỏ phần trao đổi tổ lái để kịp giờ. // During a simulation, flight information changes; a trainee wants to skip the crew briefing to stay on schedule.',
    'Giao {a} rà thông tin mới, {b} tổ chức trao đổi với cơ trưởng, {c} ghi nhận các điểm cần xác nhận trước tiếp tục bài tập. // Have {a} review the update, {b} brief the captain, and {c} record items requiring confirmation before continuing the exercise.',
    'Phiếu mô phỏng đánh dấu đủ nhưng một bước kiểm tra chéo chưa được người phụ trách xác nhận. // The simulation sheet is marked complete, but a cross-check lacks supervisor confirmation.',
    'Dừng xác nhận hoàn tất bài tập, làm rõ bước thiếu với giám sát và kiểm lại theo quy trình huấn luyện. // Withhold exercise completion, clarify the missing check with the supervisor, and reverify under training procedure.',
    'đã báo rõ thông tin thay đổi và hoàn tất kiểm tra chéo được giám sát xác nhận // reported the changed information and completed cross-checks confirmed by the supervisor',
    'xác nhận kiểm tra chéo của tổ lái // crew cross-check confirmation')

_profile('flight_attendant', 'Ngọc Bích | Hải My | Thanh Vũ',
    'Chị Thu · tiếp viên trưởng // Thu · cabin crew leader',
    'kiểm cabin, hỗ trợ hành khách và phối hợp đúng quy trình // cabin checks, passenger support, and procedural coordination',
    'kiểm khu vực cabin | hỗ trợ hành khách | ghi nhận bàn giao tổ // cabin-area checks | passenger support | crew handover records',
    'Ca huấn luyện có khách cần hỗ trợ và khu cabin chưa kiểm đủ; tiếp viên mới đang chờ phân việc. // A training shift includes a passenger needing assistance and an incompletely checked cabin area; a new crew member awaits assignment.',
    'Giao {a} rà khu vực được phân, {b} hỗ trợ khách theo hướng dẫn, {c} kèm người mới ghi và báo phần chưa xác nhận cho tiếp viên trưởng. // Have {a} check the assigned area, {b} assist under guidance, and {c} coach the newcomer to record and report outstanding items to the crew leader.',
    'Bảng cabin ghi sẵn sàng nhưng một khu vực do hai người đều nghĩ người kia đã kiểm. // The cabin sheet says ready, but two colleagues each assumed the other checked one area.',
    'Báo tiếp viên trưởng, phân người kiểm rõ khu vực bị sót và đối chiếu lại bảng trước xác nhận. // Notify the crew leader, assign a clear owner to the missed area, and reconcile the sheet before confirmation.',
    'đã phát hiện khu vực bị sót, phối hợp kiểm lại và hỗ trợ khách có ghi nhận // identified the missed area, coordinated its recheck, and documented passenger support',
    'xác nhận kiểm cabin theo khu vực // area-by-area cabin-check confirmation')

_profile('oil', 'Hữu Thành | Kim Dung | Đức Hòa',
    'Đốc công · giàn trưởng // Foreman · platform supervisor',
    'giấy phép công việc, nhận diện nguy cơ và bàn giao ca rõ // work permits, hazard recognition, and clear shift handover',
    'kiểm phạm vi giấy phép | kiểm điều kiện an toàn | ghi nhật ký ca // permit-scope review | safety-condition checks | shift logs',
    'Tổ chuẩn bị công việc nhưng điều kiện hiện trường khác mô tả giấy phép; thợ mới đang chờ bắt đầu. // A team is preparing work, but site conditions differ from the permit description and a newcomer is waiting to begin.',
    'Giao {a} đối chiếu giấy phép, {b} báo thay đổi cho cán bộ an toàn, {c} ghi trạng thái chờ và chỉ phân việc sau xác nhận có thẩm quyền. // Have {a} compare permit scope, {b} report changes to the safety officer, and {c} record the hold status; assign work only after authorized confirmation.',
    'Nhật ký ghi đã bàn giao nhưng giấy phép chưa cập nhật điều kiện thay đổi. // The log says handed over, but the permit does not reflect changed conditions.',
    'Giữ công việc ở trạng thái chờ, chuyển người có thẩm quyền rà giấy phép và kiểm hồ sơ trước xác nhận bàn giao. // Keep the work on hold, refer permit review to the authorized person, and verify records before handover confirmation.',
    'đã báo điều kiện khác giấy phép và chỉ tiếp tục sau xác nhận an toàn có thẩm quyền // reported conditions differing from the permit and proceeded only after authorized safety confirmation',
    'giấy phép phù hợp điều kiện thực tế // permits matching actual conditions')

_profile('hr_admin', 'Thùy An | Gia Phong | Ngọc Huyền',
    'Chị Huyền · trưởng phòng nhân sự // Huyền · HR manager',
    'hồ sơ chính xác, xét công bằng và bảo mật thông tin // accurate records, fair assessment, and confidential information',
    'kiểm hồ sơ ứng viên | xếp lịch phỏng vấn | soát tiêu chí đánh giá // candidate-file checks | interview scheduling | assessment-criteria review',
    'Đợt tuyển có hai ứng viên cùng giờ và một hồ sơ thiếu giấy tờ; người quen muốn được ưu tiên. // A hiring round has overlapping interviews and an incomplete application; an acquaintance asks for priority.',
    'Giao {a} kiểm thiếu sót theo cùng danh mục, {b} sửa lịch công bằng, {c} chốt tiêu chí chung trước đánh giá. // Have {a} apply the same document checklist, {b} adjust schedules fairly, and {c} agree on shared criteria before assessment.',
    'Bảng đánh giá dùng hai thang khác nhau và file chia sẻ có thông tin riêng không cần thiết. // Candidate ratings use two different scales, and the shared file contains unnecessary private details.',
    'Giữ kết quả chờ soát, thống nhất thang đánh giá và giới hạn dữ liệu chia sẻ rồi kiểm lại theo quyền. // Hold the results, standardize the rating scale, limit shared data, and recheck access.',
    'đã áp dụng tiêu chí chung và chuyển hồ sơ qua đúng kênh được phân quyền // applied shared criteria and transferred records through the authorized channel',
    'tiêu chí thống nhất và quyền nhận hồ sơ // consistent criteria and recipient access')

_profile('secretary', 'Phương Uyên | Hữu Duy | Khánh Ngọc',
    'Trưởng văn phòng Cánh Diều // Cánh Diều office manager',
    'lịch đúng ưu tiên, hồ sơ đủ và bảo mật cuộc họp // correctly prioritized schedules, complete files, and meeting confidentiality',
    'đối chiếu lịch | chuẩn bị hồ sơ họp | liên hệ đại biểu // schedule reconciliation | meeting-file preparation | attendee communication',
    'Giám đốc đổi giờ họp quan trọng trùng cuộc hẹn đối tác; tài liệu có bản nội bộ và bản được phép gửi. // The director moves a key meeting into a partner appointment; documents include internal and shareable versions.',
    'Giao {a} xác nhận ưu tiên với văn phòng, {b} tách đúng bản tài liệu, {c} báo lịch đã duyệt và lấy xác nhận. // Have {a} confirm priorities with the office, {b} separate document versions, and {c} communicate approved times and obtain confirmations.',
    'Thư mời đúng giờ nhưng đính kèm bản nội bộ có ghi chú không dành cho khách. // The invitation has the correct time but includes an internal file with notes not intended for guests.',
    'Giữ thư chưa gửi, thay đúng bản được phép, kiểm danh sách nhận và tệp đính kèm cùng người phụ trách. // Hold the message, replace the file with the approved version, and verify recipients and attachments with the responsible person.',
    'đã xử lý lịch trùng bằng xác nhận ưu tiên và gửi đúng bản hồ sơ được duyệt // resolved a schedule clash through priority confirmation and sent the approved document version',
    'xác nhận lịch và quyền chia sẻ tài liệu // schedule confirmation and document-sharing authorization')

_profile('it_helpdesk', 'Hoàng Khánh | Minh Triết | Bảo Trâm',
    'Anh Long · trưởng nhóm IT // Long · IT team leader',
    'chẩn đoán có bằng chứng, quyền truy cập đúng và bàn giao được kiểm // evidence-based diagnosis, proper access, and verified handover',
    'phân loại sự cố | kiểm quyền truy cập | xác minh khắc phục // incident triage | access checks | fix verification',
    'Nhiều máy báo lỗi đăng nhập; một người đề nghị dùng chung tài khoản quản trị cho nhanh. // Several machines report login errors; someone suggests sharing an administrator account to save time.',
    'Giao {a} gom dấu hiệu lỗi, {b} kiểm yêu cầu quyền qua người có thẩm quyền, {c} thử kết quả với người dùng mà không chia sẻ tài khoản. // Have {a} gather error evidence, {b} review access requests with the authorized owner, and {c} verify results with users without sharing accounts.',
    'Phiếu ghi đã sửa vì máy kỹ thuật đăng nhập được, nhưng người dùng thật chưa kiểm lại. // A ticket is marked fixed because a technician can log in, but the actual user has not retested.',
    'Kiểm cùng người dùng theo quyền của họ, ghi kết quả và hoàn nguyên quyền tạm theo quy trình trước đóng phiếu. // Test with the user under their permissions, record results, and remove temporary access under procedure before closure.',
    'đã xác minh nguyên nhân và khắc phục được người dùng kiểm lại với đúng quyền // verified the cause and had the user confirm the fix with appropriate permissions',
    'kiểm quyền và xác nhận người dùng // access checks and user confirmation')

_profile('railway', 'Đức Lâm | Thanh Nhàn | Quốc Thái',
    'Trưởng cung · quản lý tuyến // Section supervisor · line manager',
    'liên lạc, quy trình chắn và bàn giao ca có xác nhận // communication, crossing procedures, and confirmed shift handover',
    'đối chiếu thông tin tuyến | kiểm liên lạc | ghi bàn giao ca // line-information review | communication checks | shift-handover logs',
    'Ca huấn luyện đổi lịch tuyến, người thay ca chưa nhận đủ thông tin và thiết bị liên lạc chờ kiểm. // A training shift has a changed line schedule; the relief worker lacks information and communication equipment awaits checks.',
    'Giao {a} đối chiếu thông báo, {b} kiểm liên lạc theo quy trình, {c} xác nhận bàn giao với người đủ trách nhiệm trước đổi ca. // Have {a} reconcile notices, {b} check communications under procedure, and {c} confirm handover with the responsible worker before relief.',
    'Sổ ca đánh dấu đã báo tuyến nhưng chưa có xác nhận nhận tin từ đầu mối quy định. // The shift log marks the line notified, but the required contact has not acknowledged receipt.',
    'Báo người phụ trách, xác minh liên lạc theo quy trình và chỉ ghi hoàn tất khi có căn cứ nhận tin. // Notify the supervisor, verify communication under procedure, and record completion only with evidence of receipt.',
    'đã phát hiện thiếu xác nhận liên lạc và bàn giao đủ thông tin cho ca sau // identified a missing communication acknowledgment and handed complete information to the next shift',
    'xác nhận liên lạc và bàn giao // communication and handover acknowledgment')

_profile('nurse', 'Ngọc Liên | Thu Hạnh | Minh Hằng',
    'Chị Hoa · điều dưỡng trưởng // Hoa · head nurse',
    'đối chiếu đúng, chăm sóc trong phạm vi và chuyển cấp kịp thời // correct verification, care within scope, and timely escalation',
    'đối chiếu hồ sơ chăm sóc | quan sát và báo cáo | bàn giao ca điều dưỡng // care-record verification | observation and reporting | nursing handovers',
    'Ca nhận có người cần theo dõi thêm; điều dưỡng mới chưa nắm giới hạn việc được giao. // An incoming patient needs additional observation, and a new nurse is unsure of assigned limits.',
    'Giao {a} kiểm hồ sơ và định danh theo quy trình, {b} theo dõi và báo bất thường, {c} kèm người mới dưới phân công của điều dưỡng trưởng. // Have {a} check records and identity under procedure, {b} observe and report abnormalities, and {c} supervise the newcomer under the head nurse\'s assignment.',
    'Bảng chăm sóc ghi đã thực hiện nhưng thời điểm và người xác nhận còn trống. // The care chart marks a task completed, but its time and verifier are blank.',
    'Xác minh với người thực hiện, báo điều dưỡng trưởng phần chưa rõ và cập nhật đúng sự thật trước bàn giao. // Verify with the staff member, report uncertainty to the head nurse, and update truthfully before handover.',
    'đã nhận ra điểm bất thường, báo đúng cấp và lưu bàn giao chăm sóc được xác nhận // recognized an abnormality, escalated appropriately, and retained confirmed care-handover records',
    'xác nhận thực hiện và bàn giao chăm sóc // care-completion and handover confirmation')

_profile('lighthouse', 'Hữu Quang | Thanh Hải | Minh Hòa',
    'Chú Bảy Đèn · trạm trưởng Hòn Gió // Bảy Đèn · Hòn Gió lighthouse station chief',
    'tình trạng đèn rõ, nhật ký thật và bàn giao sự cố đầy đủ // clear light status, truthful logs, and complete incident handovers',
    'kiểm nhật ký đèn | kiểm thông tin cảnh báo | bàn giao vật tư trạm // light-log checks | warning-information checks | station-supply handover',
    'Trạm có ghi nhận đèn chập chờn; người mới định dùng nhật ký hôm trước vì chưa biết mẫu báo sự cố. // The station has reports of an intermittent light; a newcomer wants to reuse yesterday\'s log because they do not know the incident form.',
    'Giao {a} rà ghi nhận thật, {b} báo trạm trưởng theo quy trình, {c} kèm ghi nhật ký và chuẩn bị bàn giao đúng tình trạng. // Have {a} review actual observations, {b} report to the station chief under procedure, and {c} coach truthful logging and prepare an accurate handover.',
    'Nhật ký ghi đèn ổn định nhưng có một khoảng mất dữ liệu chưa được giải thích. // The log says the light was stable, but an unexplained data gap remains.',
    'Đánh dấu khoảng chưa xác minh, đối chiếu nguồn ghi với trạm trưởng và kiểm lại trước xác nhận tình trạng. // Mark the unverified interval, compare records with the station chief, and recheck before confirming status.',
    'đã ghi rõ khoảng bất thường và bàn giao sự cố cùng xác nhận của trạm trưởng // documented the abnormal interval and handed over the incident with station-chief confirmation',
    'nhật ký thực tế và xác nhận sự cố // actual logs and incident confirmation')

_profile('rescue', 'Gia Minh | Thảo Hương | Quốc Bách',
    'Chị Thảo · trưởng ca tổng đài // Thảo · dispatch shift supervisor',
    'thông tin xác minh, ưu tiên phù hợp và theo dõi điều phối // verified information, suitable priorities, and tracked dispatch',
    'xác minh vị trí | đối chiếu nguồn lực | theo dõi phản hồi đội // location verification | resource reconciliation | crew-response tracking',
    'Buổi mô phỏng có hai cuộc gọi gần nhau, địa chỉ một vụ chưa rõ và nguồn lực hiển thị đang bận. // A simulation has two nearby calls, one unclear address, and resources shown as busy.',
    'Giao {a} xác minh địa điểm, {b} kiểm nguồn lực với trưởng ca, {c} theo dõi xác nhận nhận việc; ưu tiên theo quy trình mô phỏng. // Have {a} verify locations, {b} check resources with the supervisor, and {c} track task acknowledgment; prioritize under simulation procedure.',
    'Màn hình ghi đã điều đội nhưng chưa có xác nhận đội nhận lệnh và địa điểm cuối cùng. // The screen marks a crew dispatched without crew acknowledgment or a confirmed final location.',
    'Báo trưởng ca, xác minh phản hồi đội và địa điểm qua kênh quy định, cập nhật trạng thái có căn cứ. // Notify the supervisor, verify crew acknowledgment and location through the required channel, and update status with evidence.',
    'đã làm rõ địa điểm và theo dõi đủ xác nhận nhận việc, bàn giao vụ cho ca sau // clarified the location and tracked full task acknowledgment before handing the incident to the next shift',
    'xác nhận đội nhận việc và vị trí // crew task acknowledgment and location confirmation')

_profile('lifeguard', 'Thanh Sơn | Ngọc Thảo | Đức Khang',
    'Anh Hải · trưởng nhóm cứu hộ // Hải · lifeguard team leader',
    'quan sát đủ khu, phối hợp đúng và bàn giao vị trí rõ // full-zone observation, proper coordination, and explicit station handover',
    'rà khu quan sát | phối hợp ca trực | ghi nhận bàn giao vị trí // observation-zone review | shift coordination | station-handover records',
    'Ca hồ bơi đông, hai người nghỉ đổi ca cùng lúc làm một góc khuất chưa có người nhận quan sát. // The pool is busy, and two simultaneous breaks leave a blind spot without an assigned observer.',
    'Giao {a} rà vùng quan sát, {b} bố trí thay ca với trưởng nhóm, {c} xác nhận người nhận từng vị trí trước khi rời chốt. // Have {a} review coverage, {b} arrange relief with the leader, and {c} confirm each replacement before anyone leaves a station.',
    'Bảng phân khu đủ tên nhưng một người đang hỗ trợ việc khác, khu được giao không có người quan sát. // The zone roster is complete, but one assigned person is helping elsewhere and their zone has no observer.',
    'Báo trưởng nhóm để bảo đảm lại giám sát ngay theo quy trình, xác nhận người nhận khu rồi sửa bảng theo thực tế. // Notify the leader to restore supervision immediately under procedure, confirm zone ownership, and update the roster to reality.',
    'đã nhận ra khoảng trống quan sát và phối hợp thay ca có xác nhận đủ khu // identified a coverage gap and coordinated confirmed relief across all zones',
    'xác nhận người nhận khu quan sát // observation-zone ownership confirmation')

_profile('zpop', 'Minh Kỳ | Bảo Thy | Hoàng Giang',
    'Chủ shop album · hội tiểu thương // Album shop owner · traders association',
    'đúng phiên bản, đủ quyền lợi đơn và đóng gói rõ // correct editions, complete order benefits, and clear packing',
    'kiểm phiên bản album | đối chiếu quà kèm | đóng gói vận chuyển // album-edition checks | bonus-item reconciliation | shipping preparation',
    'Đợt mở bán có ba phiên bản album và quà kèm khác nhau; người mới gom tất cả vào cùng khay. // A launch has three album editions with different bonuses; a newcomer puts them all in one tray.',
    'Giao {a} tách phiên bản theo đơn, {b} đối chiếu quà theo điều kiện công bố, {c} kiểm mã kiện rồi đóng chống hỏng. // Have {a} separate editions by order, {b} check bonuses against published conditions, and {c} verify parcel codes and protective packing.',
    'Kiện đủ album nhưng một bản khác bìa khách chọn và quà kèm chưa kiểm số lượng. // The parcel has enough albums, but one cover differs from the selected edition and bonuses have not been counted.',
    'Mở kiểm mã phiên bản và quyền lợi đơn, sửa đúng hàng rồi đối chiếu phiếu trước niêm kiện. // Check edition codes and order benefits, correct the contents, and reconcile the packing slip before sealing.',
    'đã phát hiện nhầm phiên bản, ghép đủ quà kèm và có phiếu đóng gói đối chiếu // caught an edition mismatch, included all bonuses, and retained a reconciled packing slip',
    'đối chiếu phiên bản và quà kèm // edition and bonus-item checks')

_profile('lawyer', 'Ngọc Minh | Thanh Luân | Bảo Hà',
    'Luật sư hướng dẫn · trưởng văn phòng // Supervising lawyer · law office head',
    'chứng cứ có nguồn, lập luận được soát và hồ sơ bảo mật // sourced evidence, reviewed arguments, and confidential files',
    'lập danh mục chứng cứ | đối chiếu diễn biến | soát hồ sơ bàn giao // evidence indexing | timeline comparison | handover-file review',
    'Hồ sơ tranh chấp có hai bản hợp đồng khác nhau; cộng sự mới muốn dùng bản thuận lợi hơn mà chưa kiểm nguồn. // A dispute file contains two contract versions; a junior colleague wants to use the more favorable one without verifying its source.',
    'Giao {a} ghi nguồn từng bản, {b} đối chiếu diễn biến với tài liệu gốc, {c} tổng hợp điểm chưa rõ để luật sư phụ trách soát. // Have {a} record each version\'s source, {b} compare events against originals, and {c} collect uncertainties for the supervising lawyer.',
    'Bản lập luận trích một đoạn có lợi nhưng bỏ trang phụ lục làm thay đổi ý nghĩa điều khoản. // A draft argument quotes a favorable passage but omits an appendix that changes the clause\'s meaning.',
    'Đối chiếu toàn bộ tài liệu, ghi cả điểm bất lợi và chuyển luật sư phụ trách soát trước gửi hồ sơ. // Review the full document, record adverse points as well, and obtain supervising-lawyer review before sending the file.',
    'đã tìm phụ lục bị thiếu, ghi đúng nguồn chứng cứ và trình lập luận được soát // found the missing appendix, documented evidence sources, and submitted reviewed arguments',
    'nguồn chứng cứ và soát xét toàn bộ tài liệu // evidence sources and full-document review')


if __name__ == '__main__':
    import json
    from pathlib import Path

    destination = Path(__file__).resolve().parents[1] / 'output/career-competition/content-en.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes((json.dumps(dict(strings=_EN, patterns={}), ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
